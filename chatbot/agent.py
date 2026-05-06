import json
import os
import re
import anthropic
from chatbot.data_loader import DataContext

_LANG_INSTRUCTIONS = {
    "EN": "Reply in English.",
    "FR": "Réponds en français.",
    "AR": "أجب باللغة العربية.",
}


def build_system_prompt(ctx: DataContext, language: str) -> str:
    lang = _LANG_INSTRUCTIONS.get(language, _LANG_INSTRUCTIONS["EN"])
    return f"""You are a data assistant for a Tunisian gaming center called GamefyDB.

{lang}

{ctx.schemas}

Current data summary:
{ctx.summary}

Instructions:
1. Answer any question about the data directly and concisely.
2. If a chart would help, include exactly one JSON block with key "chart_spec" in your response using this format:
```json
{{"chart_spec": {{"type": "bar|line|scatter|pie", "x": "col", "y": "col", "source": "table_key", "filter": "pandas query or empty string", "title": "Chart title"}}}}
```
3. After your answer include one JSON block with key "suggestions" containing 2-3 follow-up questions:
```json
{{"suggestions": ["Question 1?", "Question 2?", "Question 3?"]}}
```
4. If the question cannot be answered from the available data, say so clearly.
5. Never invent data.
"""


def ask(ctx: DataContext, messages: list, user_message: str, language: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    history = list(messages) + [{"role": "user", "content": user_message}]
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=build_system_prompt(ctx, language),
        messages=history,
    )
    return _parse_response(response.content[0].text)


def _parse_response(text: str) -> dict:
    chart_spec = None
    suggestions = []

    chart_match = re.search(r'```json\s*(\{[^`]*"chart_spec"[^`]*\})\s*```', text, re.DOTALL)
    if chart_match:
        try:
            chart_spec = json.loads(chart_match.group(1))["chart_spec"]
        except (json.JSONDecodeError, KeyError):
            pass

    sugg_match = re.search(r'```json\s*(\{[^`]*"suggestions"[^`]*\})\s*```', text, re.DOTALL)
    if sugg_match:
        try:
            suggestions = json.loads(sugg_match.group(1))["suggestions"]
        except (json.JSONDecodeError, KeyError):
            pass

    answer = re.sub(r'```json.*?```', '', text, flags=re.DOTALL).strip()
    if chart_spec and "title" in chart_spec:
        answer = f"{answer} [{chart_spec['title']}]" if answer else chart_spec["title"]
    return {"answer": answer, "chart_spec": chart_spec, "suggestions": suggestions}
