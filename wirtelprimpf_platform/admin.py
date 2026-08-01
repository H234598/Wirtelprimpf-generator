"""Loopback-only HTTP boundary for transactional settings and local status."""

from __future__ import annotations

import hmac
import html
import ipaddress
import json
import secrets
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlsplit

from .operational_status import OperationalStatusCollector
from .settings import (
    ChangeRequest,
    SettingsApplyFailure,
    SettingsConflict,
    SettingsError,
    SettingsLockBusy,
    SettingsManager,
    SettingsValidationFailure,
)

MAX_REQUEST_BYTES = 64 * 1024
PUBLIC_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
SECURITY_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class AdminError(RuntimeError):
    """The local-admin transport contract was violated."""


@dataclass(frozen=True, slots=True)
class AdminResponse:
    status: int
    body: str
    content_type: str = "application/json; charset=utf-8"


def validate_bind_host(host: str) -> str:
    candidate = host.strip()
    if candidate not in {"127.0.0.1", "::1"}:
        raise AdminError("admin server may bind only to 127.0.0.1 or ::1")
    return candidate


def _host_and_port(host: str) -> tuple[str, int | None]:
    candidate = host.strip().lower()
    if not candidate:
        return "", None
    try:
        parsed = urlsplit(f"//{candidate}")
        return (parsed.hostname or "").lower(), parsed.port
    except ValueError:
        return "", None


def _request_is_local(headers: dict[str, str], client_host: str, *, require_origin: bool) -> bool:
    try:
        if not ipaddress.ip_address(client_host).is_loopback:
            return False
    except ValueError:
        return False
    host, port = _host_and_port(headers.get("Host", ""))
    if host not in PUBLIC_HOSTS:
        return False
    origin = headers.get("Origin")
    if require_origin and not origin:
        return False
    if origin:
        try:
            parsed = urlsplit(origin)
            origin_port = parsed.port
        except ValueError:
            return False
        if (
            parsed.scheme not in {"http", "https"}
            or (parsed.hostname or "").lower() != host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or (port is not None and origin_port != port)
        ):
            return False
    return True


def _json_response(status: int, payload: object) -> AdminResponse:
    return AdminResponse(
        status=status,
        body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def _static_text(name: str) -> str:
    return resources.files("wirtelprimpf_platform").joinpath("static", name).read_text(encoding="utf-8")


class AdminApplication:
    def __init__(
        self,
        settings: SettingsManager,
        status: OperationalStatusCollector,
        *,
        csrf_token: str | None = None,
    ) -> None:
        self.settings = settings
        self.status = status
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)

    def _get_settings(self) -> AdminResponse:
        try:
            return _json_response(200, {"ok": True, **self.settings.snapshot().to_public_dict()})
        except SettingsLockBusy:
            return _json_response(423, {"ok": False, "error": "settings lock is busy"})
        except Exception:
            return _json_response(500, {"ok": False, "error": "settings snapshot unavailable"})

    def _get_status(self) -> AdminResponse:
        try:
            return _json_response(200, self.status.collect())
        except Exception:
            return _json_response(
                500,
                {
                    "schema_version": "1.0.0",
                    "health": "error",
                    "error": "operational status unavailable",
                },
            )

    def _post_settings(self, body: bytes) -> AdminResponse:
        try:
            payload = json.loads(body.decode("utf-8"))
            request = ChangeRequest.from_payload(payload)
            snapshot = self.settings.apply(request)
            return _json_response(200, {"ok": True, **snapshot.to_public_dict()})
        except SettingsConflict as exc:
            return _json_response(
                409,
                {
                    "ok": False,
                    "error": "conflict",
                    "conflicts": list(exc.fields),
                    "snapshot": exc.snapshot.to_public_dict(),
                },
            )
        except (UnicodeError, json.JSONDecodeError, SettingsValidationFailure) as exc:
            return _json_response(422, {"ok": False, "error": str(exc)})
        except SettingsLockBusy:
            return _json_response(423, {"ok": False, "error": "settings lock is busy"})
        except SettingsApplyFailure as exc:
            return _json_response(
                503,
                {
                    "ok": False,
                    "error": "settings transaction failed",
                    "rollback_succeeded": exc.rollback_succeeded,
                },
            )
        except SettingsError:
            return _json_response(503, {"ok": False, "error": "settings transaction unavailable"})
        except Exception:
            return _json_response(503, {"ok": False, "error": "settings transaction unavailable"})

    def handle(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        *,
        client_host: str,
    ) -> AdminResponse:
        verb = method.upper()
        effective_verb = "GET" if verb == "HEAD" else verb
        requires_origin = effective_verb != "GET"
        if not _request_is_local(headers, client_host, require_origin=requires_origin):
            return _json_response(403, {"ok": False, "error": "local request required"})
        if len(body) > MAX_REQUEST_BYTES:
            return _json_response(413, {"ok": False, "error": "request too large"})
        if path == "/api/settings" and effective_verb == "GET":
            return self._get_settings()
        if path == "/api/status" and effective_verb == "GET":
            return self._get_status()
        if path == "/api/settings" and effective_verb == "POST":
            supplied = headers.get("X-Wirtelprimpf-CSRF", "")
            if not hmac.compare_digest(supplied, self.csrf_token):
                return _json_response(403, {"ok": False, "error": "invalid CSRF token"})
            return self._post_settings(body)
        if path == "/assets/admin.css" and effective_verb == "GET":
            return AdminResponse(
                status=200,
                body=_static_text("admin.css"),
                content_type="text/css; charset=utf-8",
            )
        if path == "/assets/admin.mjs" and effective_verb == "GET":
            return AdminResponse(
                status=200,
                body=_static_text("admin.mjs"),
                content_type="text/javascript; charset=utf-8",
            )
        if path == "/" and effective_verb == "GET":
            token = html.escape(self.csrf_token, quote=True)
            return AdminResponse(
                status=200,
                body=_static_text("admin.html").replace("__CSRF_TOKEN__", token),
                content_type="text/html; charset=utf-8",
            )
        return _json_response(404, {"ok": False, "error": "not found"})


class _Handler(BaseHTTPRequestHandler):
    server_version = "WirtelprimpfAdmin/1.1"

    def _dispatch(self) -> None:
        application: AdminApplication = self.server.application  # type: ignore[attr-defined]
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0:
                raise ValueError("negative content length")
        except ValueError:
            length = MAX_REQUEST_BYTES + 1
        body = self.rfile.read(min(length, MAX_REQUEST_BYTES + 1))
        response = application.handle(
            self.command,
            self.path.split("?", 1)[0],
            {key: value for key, value in self.headers.items()},
            body,
            client_host=self.client_address[0],
        )
        encoded = response.body.encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(encoded)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    do_GET = _dispatch
    do_HEAD = _dispatch
    do_POST = _dispatch

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def serve_admin(
    settings: SettingsManager,
    status: OperationalStatusCollector,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    bind_host = validate_bind_host(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1_024 <= port <= 65_535:
        raise AdminError("admin port must be between 1024 and 65535")
    server = ThreadingHTTPServer((bind_host, port), _Handler)
    server.application = AdminApplication(settings, status)  # type: ignore[attr-defined]
    server.serve_forever()
