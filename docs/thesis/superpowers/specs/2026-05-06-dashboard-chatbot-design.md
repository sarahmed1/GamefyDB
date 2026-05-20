# GamefyDB Dashboard Assistant — Design Spec

**Date:** 2026-05-06
**Status:** Approved

## Overview

A Streamlit web app that lets anyone ask questions about the GamefyDB gaming center data in plain language (typed or spoken) and receive instant answers with dynamically generated charts. Runs locally alongside the Power BI dashboard; both read from the same CSV files.

## Goals

- Let the gaming center owner ask any question about the data without opening Power BI
- Generate charts on demand from any question
- Proactively surface anomalies on startup
- Support English, French, and Arabic

## Out of scope

- Modifying or writing data back to CSVs
- Role-based access control (separate future feature)
- Persistent conversation history across sessions
- Hosting / deployment (local use only for now)

---

## Architecture

### Files

```
app.py                          ← Streamlit entry point
chatbot/
  agent.py                      ← Claude API calls, prompt construction
  data_loader.py                ← loads all CSVs, builds context summary
  chart_generator.py            ← renders Plotly charts from Claude instructions
  voice_component.py            ← injects Web Speech API HTML into Streamlit
```

No changes to the existing pipeline (`gamefydb/`, `run.py`). The chatbot is a read-only layer on top of the existing output CSVs.

### Data sources (read-only)

All files under `output/`:

| File | Used for |
|------|----------|
| `powerbi_star/fact_transaction.csv` | Revenue, payment types, cashier activity |
| `powerbi_star/fact_session.csv` | Session durations, terminal usage |
| `powerbi_star/dim_member.csv` | Member names, IDs |
| `forecasts/forecast_revenue.csv` | Future revenue projections |
| `forecasts/session_volume.csv` | Future session projections |
| `forecasts/member_segments.csv` | K-means clusters (Heavy Users, Regulars, etc.) |
| `forecasts/member_loyalty.csv` | Loyalty tiers (Platinum, Gold, etc.) |
| `forecasts/anomalies.csv` | Detected anomalies with severity |
| `forecasts/peak_hours_by_hour.csv` | Hourly activity patterns |
| `forecasts/peak_hours_by_day.csv` | Daily activity patterns |
| `forecasts/stock_replenishment.csv` | Stock recommendations |

---

## Components

### 1. Data Loader (`data_loader.py`)

Loads all CSVs on startup into a `DataContext` object containing:
- Raw DataFrames keyed by short name (e.g. `"fact_transaction"`, `"member_loyalty"`)
- A pre-computed text summary: total revenue, date range, member count, top 5 members, recent anomaly count, current loyalty distribution
- Schema description for each DataFrame (column names + dtypes) for Claude's context

Missing CSV files are skipped with a warning — the app still starts. Claude's context only mentions tables that were successfully loaded.

The text summary and schemas are passed to Claude with every message so it always knows what data is available.

### 2. Claude Agent (`agent.py`)

**System prompt includes:**
- Role: "You are a data assistant for a Tunisian gaming center called GamefyDB."
- Data context: schema of all CSVs + pre-computed summary
- Instructions: answer any question about the data; if a chart would help, include a `chart_spec` JSON block in your response; reply in the language specified
- Language instruction: set dynamically based on selected language

**Request flow:**
1. Receive user message + full conversation history (for memory)
2. Call Claude API with system prompt + history + new message
3. Parse response: extract text answer and optional `chart_spec`
4. Return `{"answer": str, "chart_spec": dict | None, "suggestions": list[str]}`

**Chart spec format Claude returns:**
```json
{
  "chart_spec": {
    "type": "bar" | "line" | "scatter" | "pie",
    "x": "column_name",
    "y": "column_name",
    "source": "fact_transaction",   // short key matching DataContext keys
    "filter": "optional pandas query string",
    "title": "Chart title"
  }
}
```

Claude determines the chart spec from the question. The chart generator executes it.

### 3. Chart Generator (`chart_generator.py`)

Receives a `chart_spec` dict from the agent. Queries the appropriate DataFrame using the spec's `source`, `filter`, `x`, `y`, and `type` fields. Renders a Plotly figure. Returns the figure object for display in Streamlit.

Falls back gracefully if a spec is malformed — logs the error, returns `None`, bot answer still displays.

### 4. Voice Component (`voice_component.py`)

Injects a small HTML + JavaScript snippet into Streamlit using `st.components.v1.html`. Uses the browser's native Web Speech API — no external service, no cost.

- Mic button activates speech recognition
- `lang` attribute set to `en-US`, `fr-FR`, or `ar-TN` based on selected language
- On recognition result: sends the transcript back to Streamlit via `Streamlit.setComponentValue()`, which stores it in session state and triggers a rerun to populate the input box

Supported browsers: Chrome, Edge. Does not work in Firefox (Web Speech API not supported there).

---

## UI Layout

### Top bar
- App name + icon (left)
- Language switcher: EN / FR / AR buttons (right)
- Role badge: "Owner" (right, placeholder for future RBAC)

### Main area — two columns
**Left column (chat):**
- Scrollable conversation history
- Bot messages: purple avatar, dark bubble
- User messages: blue avatar, right-aligned
- Quick action buttons below history:
  - "📊 Full summary"
  - "💡 Give me advice"
  - "⚠️ Any anomalies?"
- Follow-up suggestion chips after each bot response (2–3 clickable pills)
- Input row: mic button + text input + Send button

**Right column (chart):**
- Plotly chart rendered from last chart spec
- "⬇ Download PNG" button
- "🔄 Refresh" button (re-runs last chart spec)
- Empty state: placeholder text when no chart yet

### Startup behaviour
On first load, `data_loader` checks `anomalies.csv` for entries in the last 7 days. If any exist, the bot posts a proactive opening message:
> "Hi! I noticed **2 anomalies** in the past week — want me to show you?"

Otherwise, standard greeting.

---

## Conversation Memory

The full message history for the current session is kept in `st.session_state.messages` as a list of `{"role": "user"|"assistant", "content": str}` dicts. This list is passed to Claude with every request so it can refer back to earlier messages.

Memory resets when the browser tab is closed or refreshed. No persistence to disk.

---

## Language Switching

Selected language stored in `st.session_state.language`. Affects:
- Claude system prompt instruction ("Reply in French")
- Web Speech API `lang` attribute
- Quick action button labels
- UI labels (hardcoded strings per language in a `STRINGS` dict in `app.py`)

---

## Dependencies

Add to `requirements.txt`:
```
streamlit
plotly
anthropic
```

Claude API key stored in `.env` file as `ANTHROPIC_API_KEY`. Loaded via `python-dotenv`.

---

## Running the app

```bash
# Set API key in .env first
# ANTHROPIC_API_KEY=your_key_here

python -m streamlit run app.py
```

Opens at `http://localhost:8501`.
