import pytest

from packbridge.services.knowledge_rules import (
    KnowledgeRuleError,
    extract_structured_blocks,
    merged_structured_rules,
    validate_structured_blocks,
)


def test_packbridge_yaml_and_json_blocks_are_parsed():
    text = """# Profile

~~~packbridge-yaml
field_aliases:
  Shipping Mass: package.gross_weight
continuation:
  key: package.case_number
~~~

~~~packbridge-json
{"validation": {"gross_ge_net": true}}
~~~
"""
    blocks = extract_structured_blocks(text)

    assert len(blocks) == 2
    assert blocks[0].data["field_aliases"]["Shipping Mass"] == "package.gross_weight"

    merged = merged_structured_rules(text)
    assert merged["continuation"]["key"] == "package.case_number"
    assert merged["validation"]["gross_ge_net"] is True


def test_normal_yaml_example_is_not_activated_as_packbridge_rules():
    text = """# Notes

~~~yaml
example: only
~~~
"""
    assert extract_structured_blocks(text) == []


def test_invalid_active_structured_block_is_rejected():
    text = """# Profile

~~~packbridge-yaml
field_aliases: [
~~~
"""
    with pytest.raises(KnowledgeRuleError):
        validate_structured_blocks(text)
