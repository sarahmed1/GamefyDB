# Chatbot Tool-Calling Rewrite — Design

**Date:** 2026-05-18
**Status:** Approved (brainstorming)
**Owner:** Sarra

## Problem

The current chatbot (`chatbot/agent.py`) sends a single `generate_content` call to Gemini with the user message and a long static text summary of the data. Gemini answers from the summary — it never queries the actual DataFrames.

Two failure modes observed in testing:

1. **Hallucination on missing data.** Asking "forecast member count in July 2026" returns a confident, fabricated number. We do not produce member-count forecasts (only revenue, session volume, and member segments/loyalty distributions), but nothing in the prompt says so explicitly.
2. **Wrong table / wrong chart.** Gemini emits a `chart_spec` JSON in its text reply, parsed out by regex. It frequently picks the wrong source table (e.g. plotting `fact_session`, which has no `date` column, over time) or invents column names. The chart renderer fails silently or produces nonsense.

Both stem from the same root cause: the agent improvises against a text summary instead of querying real tables.

## Goal

Replace the single-shot prompt with a Gemini **function-calling loop**. Give the agent a small set of tools that operate on the loaded DataFrames. The agent must call tools to look things up; it cannot answer numeric or chart questions from imagination.

## Non-goals

- No conversation memory beyond what `app.py` already passes in `messages`.
- No streaming responses.
- No new UI, new languages, or layout changes.
- No new forecast models. The member-count case is fixed by the agent declining correctly, not by adding a forecaster.
- No arbitrary pandas `eval` tool — too risky, not needed for the question set users actually ask.

## Architecture

```
User message
   │
   ▼
agent.ask()  ──► Gemini (with tool schemas)
   ▲                │
   │     function_call? ──yes──► dispatch to tools.py
   │                │                    │
   │                │              tool result (dict or error)
   │                │                    │
   │                └────────────────────┘
   │                │
   │      no function_call → final text
   ▼
{answer, chart_spec, suggestions}
```

Loop cap: **5 tool-call iterations** per user turn. If exceeded, return whatever final text we have plus a note that the agent ran out of steps.

## Components

### `chatbot/tools.py` (new)

Pure functions over `DataContext.tables`. Each is wrapped as a Gemini `FunctionDeclaration` and dispatched by name. All return JSON-serializable dicts; errors come back as `{"error": "..."}` so the agent can read and retry.

| Tool | Signature | Returns |
|---|---|---|
| `list_tables` | `()` | `{"tables": [{"name": str, "description": str, "row_count": int}, ...]}` |
| `describe_table` | `(name)` | `{"columns": [{"name", "dtype"}], "row_count", "sample": [3 rows as dicts]}` or `{"error"}` |
| `query_table` | `(name, filter=None, sort=None, ascending=True, limit=20)` | `{"rows": [...], "truncated": bool}`. `filter` is a pandas `query()` string. Hard cap `limit ≤ 50`. |
| `aggregate` | `(name, group_by, metric, agg)` where `agg ∈ {"sum","mean","count","min","max"}` | `{"rows": [{group_by: ..., metric: ...}, ...]}` sorted desc by metric, capped at 50 groups |
| `list_forecasts` | `()` | Hard-coded description of what we forecast and what we don't (see below) |
| `make_chart` | `(type, source, x, y, filter=None, title=None)` where `type ∈ {"bar","line","scatter","pie"}` | On success: `{"chart_spec": {...}}` (same shape `make_chart` in `chart_generator.py` already expects). On failure: `{"error": "..."}`. Validates `source ∈ ctx.tables`, `x` and `y` exist as columns. |

**`list_forecasts` content (hard-coded):**

```
We produce these forecasts:
- Revenue: weekly and monthly horizons, in TND (table: forecast_revenue)
- Session volume: weekly and monthly horizons, in sessions (table: session_volume)
- Member loyalty tiers: current distribution snapshot, not time-forecasted (table: member_loyalty)
- Member segments: current clustering, not time-forecasted (table: member_segments)
- Anomalies: detected events in historical data only (table: anomalies)

We DO NOT forecast:
- Member count / new member acquisition over time
- Per-item stock levels
- Individual member future spending
- Per-terminal or per-cashier future activity

If a user asks for a forecast we do not produce, say so clearly and offer the closest available metric.
```

The agent is instructed in its system prompt to call `list_forecasts` whenever the user asks about future predictions.

### `chatbot/agent.py` (rewrite)

```python
def ask(ctx, messages, user_message, language) -> {"answer", "chart_spec", "suggestions"}:
    client = genai.Client(...)
    tools = build_tool_declarations()           # from tools.py
    dispatcher = build_dispatcher(ctx)          # closes over ctx.tables
    history = [...messages, user_message]
    chart_spec = None

    for _ in range(MAX_ITER):
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=history,
            config=GenerateContentConfig(
                system_instruction=build_system_prompt(language),
                tools=[types.Tool(function_declarations=tools)],
            ),
        )
        fcalls = extract_function_calls(response)
        if not fcalls:
            break
        history.append(response.candidates[0].content)   # model turn
        for fc in fcalls:
            result = dispatcher(fc.name, dict(fc.args))
            if fc.name == "make_chart" and "chart_spec" in result:
                chart_spec = result["chart_spec"]
            history.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=fc.name, response=result)],
            ))

    answer, suggestions = parse_final(response.text)
    return {"answer": answer, "chart_spec": chart_spec, "suggestions": suggestions}
```

**System prompt** (much shorter than today): role, language directive, one-sentence summary of each table (from `list_tables`), and the rules:

- Use tools for any numeric claim. Never guess numbers.
- Call `list_forecasts` before answering any "predict / forecast / next month / future" question.
- Call `make_chart` to produce a chart; do not embed JSON in your reply.
- Always end your reply with a JSON block containing 2–3 `suggestions`.

**Suggestions** stay as today: one JSON block in the final text, parsed by regex. This is text-only output, not data, so the existing pattern is fine.

### `chatbot/data_loader.py` (changes)

- Drop `_build_summary` (no longer used; tools replace it).
- Keep `_build_schemas` but rename to `_build_table_descriptions` returning a `dict[name → 1-line description]` instead of a single big string. Used by `list_tables` tool and by the system prompt.
- Add a curated 1-line description per table (hand-written, not auto-generated) so the agent can pick the right one without reading every column list upfront.

### `chatbot/chart_generator.py`

No changes. `make_chart` tool produces the same `chart_spec` dict the existing renderer consumes.

### `app.py`

No changes. Same `ask()` signature, same return shape.

## Error handling

- **Tool error** (bad column, table not found, malformed filter): tool returns `{"error": "..."}`. Agent sees it and either retries with corrected args, picks a different tool, or apologizes to the user.
- **Iteration cap exceeded**: return whatever final text exists plus an appended note "(reached tool call limit)". Logged for debugging.
- **Gemini API error**: propagate to the existing try/except in `app.py:200` — unchanged.
- **`make_chart` validation**: rejects on unknown source or missing columns. Agent receives error, can retry. If it still fails by the iteration cap, the answer is returned without a chart.

## Testing

**Unit tests — `tests/test_chatbot_tools.py`** (new):
- `list_tables` returns all loaded tables
- `describe_table` happy path + unknown-table error
- `query_table` with filter + limit + sort; unknown-column error
- `aggregate` happy path; unknown-agg error
- `list_forecasts` mentions revenue, session volume, and explicitly says no member-count forecast
- `make_chart` happy path + unknown-source error + missing-column error

**Integration test — `tests/test_chatbot_agent.py`** (new):
- Mock `genai.Client` to drive a 2-turn sequence: first response is a `function_call(list_forecasts)`, second is final text. Assert tool is dispatched and final answer is returned.

**Manual smoke list (in spec, run before merge):**
- "forecast member count in July 2026" → bot says we don't forecast that, offers revenue/session volume instead. No chart.
- "top 5 members by revenue" → calls `aggregate` or `query_table` on `member_loyalty`, returns real names.
- "show me revenue for the last 30 days as a line chart" → calls `make_chart(type=line, source=fact_transaction, x=date, y=amount, filter=...)`, chart appears.
- "what's the average session duration" → calls `aggregate` on `fact_session`, returns a number.
- "any anomalies this week" → calls `query_table` on `anomalies` with a date filter.
- Switching language EN↔FR mid-conversation keeps answers correct.

## Migration / rollout

Single replacement. No flag, no parallel path. Old `agent.py` is rewritten; `data_loader.py` loses `_build_summary`; tests run; manual smoke list passes; commit.

## Open questions

None at design time. Resolve during implementation:
- Exact wording of `list_forecasts` if user adds/removes forecast types — keep it in one place in `tools.py`.
- Whether to expose `dim_member` directly or wrap it (probably direct; agent can `describe_table` it).
