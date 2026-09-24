import hashlib
import hmac
import json


def sign(body: bytes, secret: str = "app-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_verify_ok(client):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"})
    assert r.status_code == 200 and r.text == "42"


def test_verify_wrong_token(client):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"})
    assert r.status_code == 403


def test_post_valid_signature(client):
    body = json.dumps({"object": "whatsapp_business_account"}).encode()
    r = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": sign(body)})
    assert r.status_code == 200


def test_post_invalid_or_missing_signature(client):
    body = b'{"object":"x"}'
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": sign(body, "outro")}).status_code == 403
    assert client.post("/webhook", content=body).status_code == 403


def test_cors_blocks_unknown_origin(client):
    r = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
