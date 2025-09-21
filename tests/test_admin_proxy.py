from fastapi.testclient import TestClient
from app.main import app
import httpx

class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text='ok'):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json

class DummyClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        return self.responses.get(("GET", url), DummyResponse())
    def post(self, url, json=None):
        self.calls.append(("POST", url, json))
        return self.responses.get(("POST", url), DummyResponse())


def test_admin_proxies(monkeypatch):
    # Prepare fake downstream responses
    responses = {
        ("GET", "http://monero:8004/admin/queue"): DummyResponse(200, {"enabled": True}),
        ("POST", "http://monero:8004/admin/drain"): DummyResponse(200, {"status": "ok"}),
        ("GET", "http://transactions:8003/balance/123"): DummyResponse(200, {"user_id": 123, "fake_xmr": 1.0, "real_xmr": 0.0, "updated_at": "2020-01-01T00:00:00Z"}),
        ("GET", "http://monero:8004/addresses"): DummyResponse(200, [{"address": "A"}]),
    }

    def fake_client(*args, **kwargs):
        return DummyClient(responses)

    monkeypatch.setattr(httpx, 'Client', fake_client)

    client = TestClient(app)

    r1 = client.get('/queue')
    assert r1.status_code == 200
    assert r1.json()['enabled'] is True

    r2 = client.post('/drain')
    assert r2.status_code == 200
    assert r2.json()['status'] == 'ok'

    r3 = client.get('/user/123/balance')
    assert r3.status_code == 200
    assert r3.json()['user_id'] == 123

    r4 = client.get('/user/123/addresses')
    assert r4.status_code == 200
    assert isinstance(r4.json(), list)
