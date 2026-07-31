"""Loopback-only, CSRF-protected local settings application."""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import secrets
import shlex
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MAX_REQUEST_BYTES = 64 * 1024
PUBLIC_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
OPERANDI = frozenset({"classic", "story", "both"})
IMAGE_SIZES = frozenset({"1024x1024", "1536x1024", "1024x1536"})
OUTPUT_RESOLUTIONS = frozenset({"source", "2k", "4k"})
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,79}")


class AdminError(RuntimeError):
    """A local-admin security or validation contract was violated."""


@dataclass(frozen=True, slots=True)
class AdminResponse:
    status: int
    body: str
    content_type: str = "application/json; charset=utf-8"


@dataclass(frozen=True, slots=True)
class SettingSpec:
    env_name: str
    default: Any


SETTING_SPECS: dict[str, SettingSpec] = {
    "operandi": SettingSpec("WIRTELPRIMPF_OPERANDI", "story"),
    "image_model": SettingSpec("WIRTELPRIMPF_IMAGE_MODEL", "gpt-image-2"),
    "story_model": SettingSpec("WIRTELPRIMPF_STORY_MODEL", "gpt-5-mini"),
    "image_size": SettingSpec("WIRTELPRIMPF_IMAGE_SIZE", "1536x1024"),
    "output_resolution": SettingSpec("WIRTELPRIMPF_OUTPUT_RESOLUTION", "2k"),
    "generation_interval_minutes": SettingSpec("WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES", 120),
    "publish_immediately": SettingSpec("WIRTELPRIMPF_PUBLISH_IMMEDIATELY", True),
    "story_finish_parts_min": SettingSpec("WIRTELPRIMPF_STORY_FINISH_PARTS_MIN", 3),
    "story_finish_parts_max": SettingSpec("WIRTELPRIMPF_STORY_FINISH_PARTS_MAX", 5),
    "site_title": SettingSpec("WIRTELPRIMPF_SITE_TITLE", "Wirtelprimpfs Geschichtenatelier"),
    "site_intro": SettingSpec(
        "WIRTELPRIMPF_SITE_INTRO",
        "Zwei Katzen, eine Möhre, eine Maus und ein fortlaufendes Abenteuer.",
    ),
}
SECRET_ENV = {
    "openai_api_key": "OPENAI_API_KEY",
    "cloudflare_api_token": "CLOUDFLARE_API_TOKEN",
}


def validate_bind_host(host: str) -> str:
    candidate = host.strip()
    if candidate not in {"127.0.0.1", "::1"}:
        raise AdminError("admin server may bind only to 127.0.0.1 or ::1")
    return candidate


def _decode_env_value(raw: str) -> str:
    try:
        values = shlex.split(raw, comments=False, posix=True)
    except ValueError as exc:
        raise AdminError(f"invalid quoted environment value: {exc}") from exc
    if len(values) > 1:
        raise AdminError("environment values must contain exactly one shell word")
    return values[0] if values else ""


def _parse_env(text: str) -> tuple[list[str], dict[str, str]]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise AdminError(f"invalid environment key: {key!r}")
        if key in values:
            raise AdminError(f"duplicate environment key: {key}")
        values[key] = _decode_env_value(raw.strip())
    return lines, values


def _bool_value(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _validate_settings(payload: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    delete_secret_keys = {f"delete_{key}" for key in SECRET_ENV}
    unknown = set(payload) - set(SETTING_SPECS) - set(SECRET_ENV) - delete_secret_keys
    if unknown:
        raise AdminError(f"unknown settings: {sorted(unknown)}")
    result = dict(current)

    if "operandi" in payload:
        value = payload["operandi"]
        if value not in OPERANDI:
            raise AdminError("operandi must be classic, story, or both")
        result["operandi"] = value
    for key in ("image_model", "story_model"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, str) or not MODEL_RE.fullmatch(value):
                raise AdminError(f"{key} is invalid")
            result[key] = value
    if "image_size" in payload:
        if payload["image_size"] not in IMAGE_SIZES:
            raise AdminError("image_size is unsupported")
        result["image_size"] = payload["image_size"]
    if "output_resolution" in payload:
        if payload["output_resolution"] not in OUTPUT_RESOLUTIONS:
            raise AdminError("output_resolution is unsupported")
        result["output_resolution"] = payload["output_resolution"]
    if "generation_interval_minutes" in payload:
        value = payload["generation_interval_minutes"]
        if isinstance(value, bool) or not isinstance(value, int) or not 30 <= value <= 10_080:
            raise AdminError("generation_interval_minutes must be between 30 and 10080")
        result["generation_interval_minutes"] = value
    if "publish_immediately" in payload:
        if not isinstance(payload["publish_immediately"], bool):
            raise AdminError("publish_immediately must be boolean")
        result["publish_immediately"] = payload["publish_immediately"]
    for key in ("story_finish_parts_min", "story_finish_parts_max"):
        if key in payload:
            value = payload[key]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 12:
                raise AdminError(f"{key} must be between 1 and 12")
            result[key] = value
    if result["story_finish_parts_min"] > result["story_finish_parts_max"]:
        raise AdminError("story_finish_parts_min must not exceed story_finish_parts_max")
    for key, maximum in (("site_title", 120), ("site_intro", 500)):
        if key in payload:
            value = payload[key]
            if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
                raise AdminError(f"{key} must contain 1 to {maximum} characters")
            result[key] = value.strip()
    for key in SECRET_ENV:
        if key in payload:
            value = payload[key]
            if (
                not isinstance(value, str)
                or not 8 <= len(value) <= 512
                or any(character in value for character in "\r\n\x00")
            ):
                raise AdminError(f"{key} replacement is invalid")
        delete_key = f"delete_{key}"
        if delete_key in payload and not isinstance(payload[delete_key], bool):
            raise AdminError(f"{delete_key} must be boolean")
    return result


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _read(self) -> tuple[list[str], dict[str, str]]:
        if self.path.is_symlink():
            raise AdminError(f"settings path must not be a symlink: {self.path}")
        if not self.path.exists():
            return ["# Wirtelprimpf generator settings."], {}
        if not self.path.is_file():
            raise AdminError(f"settings path must be a regular file: {self.path}")
        try:
            return _parse_env(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            raise AdminError(f"cannot read settings: {exc}") from exc

    def current(self) -> dict[str, Any]:
        _, values = self._read()
        result: dict[str, Any] = {}
        for key, spec in SETTING_SPECS.items():
            raw = values.get(spec.env_name)
            if raw is None:
                result[key] = spec.default
            elif isinstance(spec.default, bool):
                result[key] = _bool_value(raw, spec.default)
            elif isinstance(spec.default, int):
                try:
                    result[key] = int(raw)
                except ValueError:
                    result[key] = spec.default
            else:
                result[key] = raw
        return result

    def public_view(self) -> dict[str, Any]:
        _, values = self._read()
        return {
            "settings": self.current(),
            "secrets": {
                "openai_api_key_present": bool(values.get("OPENAI_API_KEY")),
                "github_auth_present": bool(
                    os.environ.get("GH_TOKEN")
                    or os.environ.get("GITHUB_TOKEN")
                    or (Path.home() / ".config/gh/hosts.yml").is_file()
                ),
                "cloudflare_api_token_present": bool(
                    values.get("CLOUDFLARE_API_TOKEN")
                    or os.environ.get("CLOUDFLARE_API_TOKEN")
                    or (Path.home() / ".config/.wrangler/config/default.toml").is_file()
                ),
            },
            "invariants": {
                "archive_capacity": 50,
                "repository_pattern": "Wirtelprimpf-####",
                "domain_suffix": "telacore.org",
                "story_order_on_landing_page": "newest-first",
            },
        }

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.path.is_symlink():
            raise AdminError(f"settings path must not be a symlink: {self.path}")
        lines, _raw_values = self._read()
        validated = _validate_settings(payload, self.current())
        updates: dict[str, str | None] = {}
        for key, spec in SETTING_SPECS.items():
            if key in payload:
                value = validated[key]
                updates[spec.env_name] = "1" if value is True else "0" if value is False else str(value)
        for key, env_name in SECRET_ENV.items():
            if key in payload:
                updates[env_name] = payload[key]
            if payload.get(f"delete_{key}"):
                updates[env_name] = None

        rendered: list[str] = []
        consumed: set[str] = set()
        for line in lines:
            if "=" not in line or line.lstrip().startswith("#"):
                rendered.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key not in updates:
                rendered.append(line)
                continue
            consumed.add(key)
            value = updates[key]
            if value is not None:
                rendered.append(f"{key}={shlex.quote(value)}")
        for key in sorted(set(updates) - consumed):
            value = updates[key]
            if value is not None:
                rendered.append(f"{key}={shlex.quote(value)}")
        encoded = "\n".join(rendered).rstrip() + "\n"

        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        part = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(part, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(part, self.path)
            os.chmod(self.path, 0o600)
        finally:
            part.unlink(missing_ok=True)
        return self.public_view()


def _host_without_port(host: str) -> str:
    candidate = host.strip().lower()
    if candidate.startswith("["):
        end = candidate.find("]")
        return candidate[1:end] if end > 0 else ""
    return candidate.split(":", 1)[0]


def _request_is_local(headers: dict[str, str], client_host: str, *, require_origin: bool) -> bool:
    try:
        if not ipaddress.ip_address(client_host).is_loopback:
            return False
    except ValueError:
        return False
    host = _host_without_port(headers.get("Host", ""))
    if host not in PUBLIC_HOSTS:
        return False
    origin = headers.get("Origin")
    if require_origin and not origin:
        return False
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in PUBLIC_HOSTS:
            return False
    return True


def _json_response(status: int, payload: object) -> AdminResponse:
    return AdminResponse(status=status, body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


class AdminApplication:
    def __init__(self, store: SettingsStore, *, csrf_token: str | None = None) -> None:
        self.store = store
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)

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
        requires_origin = verb not in {"GET", "HEAD"}
        if not _request_is_local(headers, client_host, require_origin=requires_origin):
            return _json_response(403, {"ok": False, "error": "local request required"})
        if len(body) > MAX_REQUEST_BYTES:
            return _json_response(413, {"ok": False, "error": "request too large"})
        if path in {"/api/settings", "/api/status"} and verb == "GET":
            try:
                return _json_response(200, {"ok": True, **self.store.public_view()})
            except AdminError as exc:
                return _json_response(500, {"ok": False, "error": str(exc)})
        if path == "/api/settings" and verb == "POST":
            supplied = headers.get("X-Wirtelprimpf-CSRF", "")
            if not hmac.compare_digest(supplied, self.csrf_token):
                return _json_response(403, {"ok": False, "error": "invalid CSRF token"})
            try:
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise AdminError("request body must be a JSON object")
                view = self.store.update(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, AdminError) as exc:
                return _json_response(422, {"ok": False, "error": str(exc)})
            return _json_response(200, {"ok": True, **view})
        if path == "/" and verb == "GET":
            return AdminResponse(
                status=200,
                body=ADMIN_HTML.replace("__CSRF_TOKEN__", self.csrf_token),
                content_type="text/html; charset=utf-8",
            )
        return _json_response(404, {"ok": False, "error": "not found"})


class _Handler(BaseHTTPRequestHandler):
    server_version = "WirtelprimpfAdmin/1.0"

    def _dispatch(self) -> None:
        application: AdminApplication = self.server.application  # type: ignore[attr-defined]
        try:
            length = int(self.headers.get("Content-Length", "0"))
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
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    do_GET = _dispatch
    do_HEAD = _dispatch
    do_POST = _dispatch

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def serve_admin(store: SettingsStore, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    bind_host = validate_bind_host(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1_024 <= port <= 65_535:
        raise AdminError("admin port must be between 1024 and 65535")
    server = ThreadingHTTPServer((bind_host, port), _Handler)
    server.application = AdminApplication(store)  # type: ignore[attr-defined]
    server.serve_forever()


ADMIN_HTML = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="csrf-token" content="__CSRF_TOKEN__"><title>Wirtelprimpf · Ateliersteuerung</title>
<style>
:root{color-scheme:dark;--ink:#f8eddd;--muted:#cbbdaf;--card:#241d2cdd;--line:#6f5b77;--gold:#f2b85b;--mint:#79d7b5;--rose:#ef879c}*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,sans-serif;color:var(--ink);background:radial-gradient(circle at 15% 10%,#51354d,transparent 38%),radial-gradient(circle at 85% 0,#164b4b,transparent 35%),#15121b;min-height:100vh}.wrap{width:min(1040px,calc(100% - 2rem));margin:auto;padding:3rem 0 5rem}header{display:grid;gap:.6rem;margin-bottom:1.5rem}h1{font:700 clamp(2rem,7vw,4.8rem)/.95 Georgia,serif;margin:0;max-width:12ch}header p{color:var(--muted);max-width:65ch}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:1rem}.card{background:var(--card);border:1px solid var(--line);border-radius:1.4rem;padding:1.2rem;box-shadow:0 20px 50px #0006}h2{font:700 1.25rem Georgia,serif;margin:.1rem 0 1rem;color:var(--gold)}label{display:grid;gap:.35rem;margin:.8rem 0;color:var(--muted)}input,select,textarea,button{font:inherit}input,select,textarea{width:100%;background:#110e16;color:var(--ink);border:1px solid var(--line);border-radius:.7rem;padding:.7rem}textarea{min-height:7rem;resize:vertical}.check{display:flex;align-items:center;gap:.65rem}.check input{width:auto}button{border:0;border-radius:999px;padding:.8rem 1.25rem;background:var(--gold);color:#201520;font-weight:800;cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid var(--mint);outline-offset:2px}.status{min-height:1.5rem;color:var(--mint)}.secret{border-color:var(--rose)}code{color:var(--mint)}
</style></head><body><main class="wrap"><header><span>Lokale Steuerzentrale · nur Loopback</span><h1>Das Geschichtenatelier</h1><p>Generator, Story, Zeitplan und Publikation an einem sicheren Ort. Geheimnisse werden niemals angezeigt; ein Schlüssel kann nur ersetzt oder gelöscht werden.</p></header>
<form id="settings"><div class="grid"><section class="card"><h2>Generierung</h2><label>Modus<select name="operandi"><option>classic</option><option>story</option><option>both</option></select></label><label>Bildmodell<input name="image_model"></label><label>Storymodell<input name="story_model"></label><label>API-Bildgröße<select name="image_size"><option>1024x1024</option><option>1536x1024</option><option>1024x1536</option></select></label><label>Ausgabeauflösung<select name="output_resolution"><option>source</option><option>2k</option><option>4k</option></select></label></section>
<section class="card"><h2>Story & Zeitplan</h2><label>Intervall in Minuten<input type="number" min="30" max="10080" name="generation_interval_minutes"></label><label>Minimale Abschlussteile<input type="number" min="1" max="12" name="story_finish_parts_min"></label><label>Maximale Abschlussteile<input type="number" min="1" max="12" name="story_finish_parts_max"></label><label class="check"><input type="checkbox" name="publish_immediately"> Nach Erfolg sofort publizieren</label><p>Fix: <code>50 vollständige Bände</code> je Archiv; danach vollautomatische Rotation.</p></section>
<section class="card"><h2>Website</h2><label>Seitentitel<input name="site_title" maxlength="120"></label><label>Einleitung<textarea name="site_intro" maxlength="500"></textarea></label><p>Die aktuelle Story erscheint auf der Landingpage verbindlich mit dem neuesten Teil zuerst.</p></section>
<section class="card"><h2>Geheimnisse</h2><label>OpenAI-Schlüssel ersetzen<input class="secret" type="password" name="openai_api_key" autocomplete="new-password" placeholder="bleibt leer, wenn unverändert"></label><label class="check"><input type="checkbox" name="delete_openai_api_key"> vorhandenen OpenAI-Schlüssel löschen</label><label>Cloudflare-Token ersetzen<input class="secret" type="password" name="cloudflare_api_token" autocomplete="new-password" placeholder="nur für Archivrotation nötig"></label><label class="check"><input type="checkbox" name="delete_cloudflare_api_token"> vorhandenen Cloudflare-Token löschen</label><p id="secret-state"></p></section></div><p><button type="submit">Sicher anwenden</button></p><p class="status" id="status" role="status" aria-live="polite"></p></form></main>
<script>
const form=document.querySelector('#settings'),status=document.querySelector('#status'),csrf=document.querySelector('meta[name="csrf-token"]').content;
function fill(data){for(const [key,value] of Object.entries(data.settings)){const el=form.elements.namedItem(key);if(!el)continue;if(el.type==='checkbox')el.checked=Boolean(value);else el.value=value}document.querySelector('#secret-state').textContent=`OpenAI: ${data.secrets.openai_api_key_present?'vorhanden':'fehlt'} · Cloudflare: ${data.secrets.cloudflare_api_token_present?'vorhanden':'fehlt'} · GitHub-Anmeldung: ${data.secrets.github_auth_present?'vorhanden':'fehlt'}`}
fetch('/api/settings',{cache:'no-store'}).then(r=>r.json()).then(fill).catch(()=>status.textContent='Einstellungen konnten nicht geladen werden.');
form.addEventListener('submit',async event=>{event.preventDefault();status.textContent='Prüfe und speichere …';const payload={};for(const name of ['operandi','image_model','story_model','image_size','output_resolution','site_title','site_intro'])payload[name]=form.elements.namedItem(name).value;for(const name of ['generation_interval_minutes','story_finish_parts_min','story_finish_parts_max'])payload[name]=Number(form.elements.namedItem(name).value);for(const name of ['publish_immediately','delete_openai_api_key','delete_cloudflare_api_token'])payload[name]=form.elements.namedItem(name).checked;for(const name of ['openai_api_key','cloudflare_api_token']){const secret=form.elements.namedItem(name);if(secret.value)payload[name]=secret.value}const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json','X-Wirtelprimpf-CSRF':csrf},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok){status.textContent=data.error||'Änderung abgelehnt.';return}for(const name of ['openai_api_key','cloudflare_api_token'])form.elements.namedItem(name).value='';for(const name of ['delete_openai_api_key','delete_cloudflare_api_token'])form.elements.namedItem(name).checked=false;fill(data);status.textContent='Atomar gespeichert und validiert.'});
</script></body></html>"""
