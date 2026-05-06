import pytest
from chatbot.agent import _parse_response, build_system_prompt
from chatbot.data_loader import DataContext


def _ctx():
    return DataContext(tables={}, summary="Total revenue: 5000 TND", schemas="- fact_transaction: date, amount")


def test_parse_answer_only():
    result = _parse_response("Revenue is doing well this month.")
    assert result["answer"] == "Revenue is doing well this month."
    assert result["chart_spec"] is None
    assert result["suggestions"] == []


def test_parse_chart_spec():
    text = '''Here is the revenue chart.

```json
{"chart_spec": {"type": "bar", "x": "date", "y": "amount", "source": "fact_transaction", "filter": "", "title": "Revenue"}}
```
'''
    result = _parse_response(text)
    assert result["chart_spec"] is not None
    assert result["chart_spec"]["type"] == "bar"
    assert result["chart_spec"]["source"] == "fact_transaction"
    assert "revenue" in result["answer"].lower()


def test_parse_suggestions():
    text = '''Good question.

```json
{"suggestions": ["What is the top terminal?", "Show member loyalty distribution"]}
```
'''
    result = _parse_response(text)
    assert len(result["suggestions"]) == 2
    assert "What is the top terminal?" in result["suggestions"]


def test_parse_malformed_json_is_safe():
    text = '```json\n{"chart_spec": {broken}\n```'
    result = _parse_response(text)
    assert result["chart_spec"] is None


def test_system_prompt_contains_language_instruction():
    prompt = build_system_prompt(_ctx(), "FR")
    assert "français" in prompt.lower() or "french" in prompt.lower() or "fr" in prompt.lower()


def test_system_prompt_contains_data_summary():
    prompt = build_system_prompt(_ctx(), "EN")
    assert "5000 TND" in prompt
