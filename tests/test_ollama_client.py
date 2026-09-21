from pydantic import BaseModel

from packbridge.mapper_schemas import MapperResult
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


class StructuredReply(BaseModel):
    message: str
    proposed_changes: list[dict]


def test_chat_json_uses_schema_and_parses_message_content():
    session = FakeSession(
        {
            "message": {
                "content": '{"message":"Done","proposed_changes":[]}'
            }
        }
    )
    client = OllamaClient("http://localhost:11434", "qwen3:14b", session=session)

    result = client.chat_json(
        [{"role": "user", "content": "Hello"}],
        StructuredReply,
        system_prompt="Return structured output",
    )

    assert result.available is True
    assert result.value.message == "Done"
    assert result.value.proposed_changes == []
    assert session.last_json["format"]["type"] == "object"
    assert session.last_json["options"]["temperature"] == 0



def test_cloud_model_scalar_shorthand_is_normalised_to_mapper_schema():
    session = FakeSession(
        {
            "response": '{"vendor":"ACME","packages":[{"case_number":"CR-1","gross_weight":410,"net_weight":365,"items":[{"item_number":"AC-500","description":"Control cabinet","quantity":1,"uom":"EA"}]}]}'
        }
    )
    client = OllamaClient(
        "http://localhost:11434",
        "gpt-oss:120b-cloud",
        session=session,
    )

    result = client.generate_json("Map this packing list", MapperResult)

    assert result.available is True
    assert result.model == "gpt-oss:120b-cloud"
    assert result.value.packages[0].case_number.value == "CR-1"
    assert result.value.packages[0].gross_weight.value == 410
    assert result.value.packages[0].items[0].item_number.value == "AC-500"
    assert session.last_json["model"] == "gpt-oss:120b-cloud"
    assert session.last_json["format"] == "json"


def test_double_encoded_json_is_unwrapped_before_schema_validation():
    session = FakeSession(
        {
            "response": '" + JSON.stringify('{"message":"Done","proposed_changes":[],"data_queries":[]}') + "'
        }
    )
    client = OllamaClient("http://localhost:11434", "gpt-oss:120b-cloud", session=session)

    result = client.chat_json(
        [{"role": "user", "content": "Hello"}],
        StructuredReply,
        system_prompt="Return structured output",
    )

    assert result.available is True
    assert result.value.message == "Done"
