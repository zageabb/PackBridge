from packbridge.services.ollama_client import OllamaClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.content = b"{}"
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.last_json = None

    def request(self, method, url, json=None, timeout=None):
        self.last_json = json
        return FakeResponse(self.payload)


def test_generate_json_uses_temperature_zero_and_schema():
    session = FakeSession({"response": '{"value": 5}'})
    client = OllamaClient("http://localhost:11434", "qwen3:14b", session=session)

    result = client.generate_json("Return JSON")

    assert result.available is True
    assert result.value == {"value": 5}
    assert session.last_json["options"]["temperature"] == 0
    assert session.last_json["format"] == "json"


def test_list_models_returns_names():
    session = FakeSession({"models": [{"name": "qwen3:14b"}, {"name": "qwen3:8b"}]})
    client = OllamaClient("http://localhost:11434", "qwen3:14b", session=session)

    result = client.list_models()

    assert result.value == ["qwen3:14b", "qwen3:8b"]
