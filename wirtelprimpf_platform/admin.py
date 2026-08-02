"""Loopback-only HTTP boundary for transactional settings and local status."""

from __future__ import annotations

import hmac
import html
import ipaddress
import json
import secrets
import time
from collections.abc import Iterable, Mapping
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
REQUEST_BODY_TIMEOUT_SECONDS = 2.0
PUBLIC_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
SECURITY_REQUEST_HEADERS = frozenset({"host", "origin", "x-wirtelprimpf-csrf"})
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


def _normalize_request_headers(
    headers: Mapping[str, str] | Iterable[tuple[str, str]],
) -> dict[str, str] | None:
    items = headers.items() if isinstance(headers, Mapping) else headers
    normalized: dict[str, str] = {}
    for name, value in items:
        if not isinstance(name, str) or not isinstance(value, str):
            return None
        normalized_name = name.lower()
        if normalized_name in SECURITY_REQUEST_HEADERS and normalized_name in normalized:
            return None
        normalized.setdefault(normalized_name, value)
    return normalized


def _request_is_local(headers: Mapping[str, str], client_host: str, *, require_origin: bool) -> bool:
    try:
        if not ipaddress.ip_address(client_host).is_loopback:
            return False
    except ValueError:
        return False
    host, port = _host_and_port(headers.get("host", ""))
    if host not in PUBLIC_HOSTS:
        return False
    origin = headers.get("origin")
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
            or origin_port != port
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
        headers: Mapping[str, str] | Iterable[tuple[str, str]],
        body: bytes,
        *,
        client_host: str,
    ) -> AdminResponse:
        verb = method.upper()
        effective_verb = "GET" if verb == "HEAD" else verb
        requires_origin = effective_verb != "GET"
        normalized_headers = _normalize_request_headers(headers)
        if normalized_headers is None or not _request_is_local(
            normalized_headers,
            client_host,
            require_origin=requires_origin,
        ):
            return _json_response(403, {"ok": False, "error": "local request required"})
        if len(body) > MAX_REQUEST_BYTES:
            return _json_response(413, {"ok": False, "error": "request too large"})
        if path == "/api/settings" and effective_verb == "GET":
            return self._get_settings()
        if path == "/api/status" and effective_verb == "GET":
            return self._get_status()
        if path == "/api/settings" and effective_verb == "POST":
            supplied = normalized_headers.get("x-wirtelprimpf-csrf", "")
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
    request_body_timeout_seconds = REQUEST_BODY_TIMEOUT_SECONDS

    def _write_admin_response(self, response: AdminResponse) -> None:
        encoded = response.body.encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(encoded)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def _dispatch(self) -> None:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            if self.command == "POST":
                self._write_admin_response(
                    _json_response(411, {"ok": False, "error": "content length required"})
                )
                return
            length = 0
        else:
            normalized_length = raw_length.strip()
            if not normalized_length.isdecimal():
                self._write_admin_response(
                    _json_response(400, {"ok": False, "error": "invalid content length"})
                )
                return
            try:
                length = int(normalized_length)
            except ValueError:
                self._write_admin_response(
                    _json_response(400, {"ok": False, "error": "invalid content length"})
                )
                return
        if length > MAX_REQUEST_BYTES:
            self.close_connection = True
            self._write_admin_response(
                _json_response(413, {"ok": False, "error": "request too large"})
            )
            return
        if self.command in {"GET", "HEAD"} and length:
            self.close_connection = True
            self._write_admin_response(
                _json_response(400, {"ok": False, "error": "request body not allowed"})
            )
            return
        application: AdminApplication = self.server.application  # type: ignore[attr-defined]
        body = b""
        if length:
            previous_timeout = self.connection.gettimeout()
            body_timed_out = False
            try:
                deadline = time.monotonic() + self.request_body_timeout_seconds
                chunks: list[bytes] = []
                remaining = length
                read_chunk = getattr(self.rfile, "read1", self.rfile.read)
                while remaining:
                    remaining_seconds = deadline - time.monotonic()
                    if remaining_seconds <= 0:
                        raise TimeoutError
                    self.connection.settimeout(remaining_seconds)
                    chunk = read_chunk(remaining)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                body = b"".join(chunks)
            except TimeoutError:
                body_timed_out = True
            finally:
                self.connection.settimeout(previous_timeout)
            if body_timed_out:
                self.close_connection = True
                self._write_admin_response(
                    _json_response(408, {"ok": False, "error": "request body timeout"})
                )
                return
            if len(body) != length:
                self.close_connection = True
                self._write_admin_response(
                    _json_response(400, {"ok": False, "error": "incomplete request body"})
                )
                return
        response = application.handle(
            self.command,
            self.path.split("?", 1)[0],
            tuple(self.headers.raw_items()),
            body,
            client_host=self.client_address[0],
        )
        self._write_admin_response(response)

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
