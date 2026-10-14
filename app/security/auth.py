"""Authentication primitives isolated from FastAPI assembly and service startup."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

AUTH_COOKIE_NAME = "navil_session"
AUTH_SESSION_SECONDS = 12 * 60 * 60
AUTH_PASSWORD_ITERATIONS = 600_000


def load_auth_secret(data_dir):
    """Load or atomically create the persistent signing secret with private permissions."""
    path = Path(data_dir) / "app_auth.key"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        secret = path.read_bytes()
        if len(secret) < 32:
            raise RuntimeError("The app authentication key is missing or invalid.")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return secret
    else:
        secret = secrets.token_bytes(32)
        with os.fdopen(fd, "wb") as handle:
            handle.write(secret)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return secret


def valid_auth_username(username):
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", str(username or "")))


def valid_auth_password(password):
    return isinstance(password, str) and 12 <= len(password) <= 1024


def password_digest(password, salt, iterations=AUTH_PASSWORD_ITERATIONS):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()


def make_session_token(username, secret, now=None, session_seconds=AUTH_SESSION_SECONDS):
    issued_at = int(time.time() if now is None else now)
    payload = json.dumps(
        {"u": username, "exp": issued_at + session_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
    signed = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return encoded + "." + signed


def session_username(token, secret, settings_reader, now=None):
    if not token or "." not in token:
        return None
    encoded, supplied_signature = token.rsplit(".", 1)
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
    ).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        payload_bytes = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(payload_bytes.decode("utf-8"))
        settings = settings_reader()
        current_time = int(time.time() if now is None else now)
        if payload.get("exp", 0) <= current_time:
            return None
        if payload.get("u") != settings.get("app_auth_username"):
            return None
        return payload["u"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
