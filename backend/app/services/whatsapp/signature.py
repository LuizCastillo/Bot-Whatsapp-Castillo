import hashlib
import hmac


def verify_signature(body: bytes, header: str | None, app_secret: str) -> bool:
    """Valida X-Hub-Signature-256 (HMAC-SHA256 do corpo bruto)."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))
