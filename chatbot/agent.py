import json
import os
import re
from google import genai
from google.genai import types
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

Source selection rules — pick the right table for the question:
- Revenue or income trend over time → `fact_transaction` (filter `type == 'Income'`, x=`date`, y=`amount`).
- Future revenue projections → `forecast_revenue` (use `filter "granularity == 'weekly'"` or `'monthly'`, y=`yhat`).
- Future session counts → `session_volume` (same granularity filter, y=`yhat`).
- Session duration / type breakdown → `fact_session` (NO date column — never plot it over time).
- Anomalies / unusual days → `anomalies` only when the user asks about anomalies; do NOT use it as a generic revenue source.
- Member rankings, top spenders → `member_loyalty` or `dim_member`.
- Loyalty tier distribution → `member_loyalty` (x=`loyalty_tier`).
- Segments / clusters → `member_segments` (x=`segment_label`).
- Hourly / daily activity patterns → `peak_hours_by_hour` or `peak_hours_by_day`.

Only include a chart when one is genuinely useful. Don't add a chart to a pure-text question.
"""


def ask(ctx: DataContext, messages: list, user_message: str, language: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
    client = genai.Client(api_key=api_key)
    history = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    history.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(ctx, language),
        ),
    )
    return _parse_response(response.text)


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
    return {"answer": answer, "chart_spec": chart_spec, "suggestions": suggestions}
