# GamefyDB Dashboard Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit chatbot that answers any question about GamefyDB CSV data in plain language, renders dynamic Plotly charts, supports voice input and EN/FR/AR language switching, and proactively alerts on anomalies.

**Architecture:** Four focused modules under `chatbot/` (data_loader, agent, chart_generator, voice_component) wired together in a single `app.py`. No changes to the existing pipeline. The chatbot is a read-only layer on top of `output/` CSVs.

**Tech Stack:** Streamlit, Plotly, Anthropic Python SDK, Web Speech API (browser-native, free), python-dotenv

---

## File Map

| File | Responsibility |
|------|---------------|
| `app.py` | Streamlit UI — layout, session state, rendering |
| `chatbot/__init__.py` | Empty package marker |
| `chatbot/data_loader.py` | Load CSVs → DataContext (tables + summary + schemas) |
| `chatbot/agent.py` | Claude API call + response parsing |
| `chatbot/chart_generator.py` | chart_spec dict → Plotly figure |
| `chatbot/voice_html/index.html` | Web Speech API component HTML |
| `chatbot/voice_component.py` | declare_component wrapper for voice HTML |
| `tests/test_data_loader.py` | DataContext tests |
| `tests/test_chart_generator.py` | Chart generation tests |
| `tests/test_agent.py` | Response parsing tests (no API calls) |
| `.env.example` | API key template |
| `launch.bat` | Double-click launcher |

**Python path (use this for all commands):**
`C:/Users/sarah/AppData/Local/Python/bin/python`

---

## Task 1: Setup — dependencies, package scaffold, launcher

**Files:**
- Modify: `requirements.txt`
- Create: `chatbot/__init__.py`
- Create: `.env.example`
- Create: `launch.bat`

- [ ] **Step 1: Add dependencies to requirements.txt**

Open `requirements.txt` and append these lines:
```
streamlit
plotly
anthropic
python-dotenv
kaleido
```

- [ ] **Step 2: Install new dependencies**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pip install streamlit plotly anthropic python-dotenv kaleido
```

Expected: all packages install without errors. Kaleido may take a moment — it enables PNG chart export.

- [ ] **Step 3: Create chatbot package**

Create `chatbot/__init__.py` with empty content:
```python
```

- [ ] **Step 4: Create .env.example**

Create `.env.example`:
```
ANTHROPIC_API_KEY=your_key_here
```

Also create `.env` with your real API key (never commit this file):
```
ANTHROPIC_API_KEY=sk-ant-...your real key...
```

Add `.env` to `.gitignore` if not already there.

- [ ] **Step 5: Create launch.bat**

Create `launch.bat` in the project root:
```bat
@echo off
"C:\Users\sarah\AppData\Local\Python\bin\python" -m streamlit run app.py
pause
```

- [ ] **Step 6: Commit**

```
git add requirements.txt chatbot/__init__.py .env.example launch.bat
git commit -m "feat: scaffold chatbot package and add dependencies"
```

---

## Task 2: Data Loader

**Files:**
- Create: `chatbot/data_loader.py`
- Create: `tests/test_data_loader.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_data_loader.py`:
```python
import pandas as pd
import pytest
from io import StringIO
from unittest.mock import patch
from pathlib import Path
from chatbot.data_loader import DataContext, _build_schemas, _build_summary, recent_anomaly_count, load_data, CSV_MAP


def _make_tables():
    tx = pd.DataFrame({
        "tx_id": [1, 2],
        "date": ["2026-01-10", "2026-01-11"],
        "type": ["Income", "Income"],
        "amount": [100.0, 200.0],
        "cashier_id": [1, 1],
        "terminal_id": [1, 2],
    })
    members = pd.DataFrame({
        "member_id": [1, 2],
        "username": ["alice", "bob"],
        "firstname": ["Alice", "Bob"],
        "lastname": ["A", "B"],
    })
    loyalty = pd.DataFrame({
        "member_id": [1, 2],
        "username": ["alice", "bob"],
        "firstname": ["Alice", "Bob"],
        "lastname": ["A", "B"],
        "total_tnd": [500.0, 200.0],
        "duration_min": [1000, 500],
        "m_score": [4, 3],
        "f_score": [4, 3],
        "fm_score": [8, 6],
        "loyalty_tier": ["Platinum", "Gold"],
    })
    anomalies = pd.DataFrame({
        "date": [pd.Timestamp.now().strftime("%Y-%m-%d")],
        "series": ["revenue"],
        "severity": ["severe"],
    })
    return {"fact_transaction": tx, "dim_member": members, "member_loyalty": loyalty, "anomalies": anomalies}


def test_build_schemas_includes_all_keys():
    tables = _make_tables()
    schemas = _build_schemas(tables)
    assert "fact_transaction" in schemas
    assert "dim_member" in schemas


def test_build_summary_includes_revenue():
    tables = _make_tables()
    summary = _build_summary(tables)
    assert "300.00 TND" in summary


def test_build_summary_includes_member_count():
    tables = _make_tables()
    summary = _build_summary(tables)
    assert "2" in summary


def test_recent_anomaly_count_today():
    ctx = DataContext(tables=_make_tables())
    assert recent_anomaly_count(ctx) == 1


def test_recent_anomaly_count_no_anomalies_table():
    ctx = DataContext(tables={})
    assert recent_anomaly_count(ctx) == 0


def test_load_data_skips_missing_files(tmp_path):
    ctx = load_data(base_dir=str(tmp_path))
    assert isinstance(ctx, DataContext)
    assert len(ctx.tables) == 0
    assert ctx.summary == ""
```

- [ ] **Step 2: Run to confirm failures**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py -v
```

Expected: all 6 tests FAIL with `ModuleNotFoundError: No module named 'chatbot.data_loader'`

- [ ] **Step 3: Implement data_loader.py**

Create `chatbot/data_loader.py`:
```python
from dataclasses import dataclass, field
import pandas as pd
from pathlib import Path
import warnings

CSV_MAP = {
    "fact_transaction": "output/powerbi_star/fact_transaction.csv",
    "fact_session": "output/powerbi_star/fact_session.csv",
    "dim_member": "output/powerbi_star/dim_member.csv",
    "forecast_revenue": "output/forecasts/forecast_revenue.csv",
    "session_volume": "output/forecasts/session_volume.csv",
    "member_segments": "output/forecasts/member_segments.csv",
    "member_loyalty": "output/forecasts/member_loyalty.csv",
    "anomalies": "output/forecasts/anomalies.csv",
    "peak_hours_by_hour": "output/forecasts/peak_hours_by_hour.csv",
    "peak_hours_by_day": "output/forecasts/peak_hours_by_day.csv",
    "stock_replenishment": "output/forecasts/stock_replenishment.csv",
}


@dataclass
class DataContext:
    tables: dict = field(default_factory=dict)
    summary: str = ""
    schemas: str = ""


def load_data(base_dir: str = ".") -> DataContext:
    ctx = DataContext()
    base = Path(base_dir)
    for key, rel_path in CSV_MAP.items():
        path = base / rel_path
        if path.exists():
            ctx.tables[key] = pd.read_csv(path)
        else:
            warnings.warn(f"CSV not found, skipping: {path}")
    ctx.schemas = _build_schemas(ctx.tables)
    ctx.summary = _build_summary(ctx.tables)
    return ctx


def _build_schemas(tables: dict) -> str:
    if not tables:
        return ""
    lines = ["Available tables and their columns:\n"]
    for key, df in tables.items():
        cols = ", ".join(f"{c} ({t})" for c, t in zip(df.columns, df.dtypes))
        lines.append(f"- {key}: {cols}")
    return "\n".join(lines)


def _build_summary(tables: dict) -> str:
    parts = []
    if "fact_transaction" in tables:
        df = tables["fact_transaction"].copy()
        income = df[df["type"] == "Income"]["amount"].sum()
        df["date"] = pd.to_datetime(df["date"])
        date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
        parts.append(f"Total revenue: {income:,.2f} TND | Data range: {date_range}")
    if "dim_member" in tables:
        parts.append(f"Total members: {len(tables['dim_member'])}")
    if "member_loyalty" in tables:
        dist = tables["member_loyalty"]["loyalty_tier"].value_counts().to_dict()
        top5 = tables["member_loyalty"].nlargest(5, "total_tnd")[["username", "total_tnd"]].to_dict("records")
        parts.append(f"Loyalty tiers: {dist}")
        parts.append(f"Top 5 members by revenue: {top5}")
    if "anomalies" in tables:
        df = tables["anomalies"].copy()
        df["date"] = pd.to_datetime(df["date"])
        recent = df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        parts.append(f"Recent anomalies (last 7 days): {len(recent)}")
    return "\n".join(parts)


def recent_anomaly_count(ctx: DataContext) -> int:
    if "anomalies" not in ctx.tables:
        return 0
    df = ctx.tables["anomalies"].copy()
    df["date"] = pd.to_datetime(df["date"])
    return len(df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)])
```

- [ ] **Step 4: Run tests — expect PASS**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```
git add chatbot/data_loader.py tests/test_data_loader.py
git commit -m "feat: add DataContext loader with CSV mapping and summary builder"
```

---

## Task 3: Chart Generator

**Files:**
- Create: `chatbot/chart_generator.py`
- Create: `tests/test_chart_generator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_chart_generator.py`:
```python
import pandas as pd
import pytest
from chatbot.chart_generator import make_chart


def _tables():
    return {
        "fact_transaction": pd.DataFrame({
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "amount": [100.0, 150.0, 200.0],
            "type": ["Income", "Income", "Income"],
            "category": ["Computer Incomes", "Order Incomes", "Computer Incomes"],
        })
    }


def test_bar_chart_returns_figure():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "fact_transaction", "filter": "", "title": "Revenue"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_line_chart_returns_figure():
    spec = {"type": "line", "x": "date", "y": "amount", "source": "fact_transaction", "filter": "", "title": "Revenue"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_filter_is_applied():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "fact_transaction",
            "filter": "category == 'Computer Incomes'", "title": "Filtered"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_missing_source_returns_none():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "nonexistent", "filter": "", "title": "X"}
    fig = make_chart(spec, _tables())
    assert fig is None


def test_bad_column_returns_none():
    spec = {"type": "bar", "x": "bad_col", "y": "amount", "source": "fact_transaction", "filter": "", "title": "X"}
    fig = make_chart(spec, _tables())
    assert fig is None


def test_malformed_spec_returns_none():
    fig = make_chart({}, _tables())
    assert fig is None
```

- [ ] **Step 2: Run to confirm failures**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_chart_generator.py -v
```

Expected: all 6 tests FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement chart_generator.py**

Create `chatbot/chart_generator.py`:
```python
import sys
import plotly.express as px
import pandas as pd


_DARK = dict(paper_bgcolor="#0f172a", plot_bgcolor="#1e293b", font_color="#e2e8f0")


def make_chart(chart_spec: dict, tables: dict):
    try:
        source = chart_spec.get("source")
        if not source or source not in tables:
            return None

        df = tables[source].copy()

        filter_expr = chart_spec.get("filter", "")
        if filter_expr:
            df = df.query(filter_expr)

        x = chart_spec.get("x")
        y = chart_spec.get("y")
        title = chart_spec.get("title", "")
        chart_type = chart_spec.get("type", "bar")

        if not x or not y:
            return None
        if x not in df.columns or y not in df.columns:
            return None

        # Group + count if y column is non-numeric
        if not pd.api.types.is_numeric_dtype(df[y]):
            df = df.groupby(x).size().reset_index(name=y)

        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title)
        else:
            fig = px.bar(df, x=x, y=y, title=title)

        fig.update_layout(**_DARK)
        return fig

    except Exception as e:
        print(f"Chart error: {e}", file=sys.stderr)
        return None
```

- [ ] **Step 4: Run tests — expect PASS**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_chart_generator.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```
git add chatbot/chart_generator.py tests/test_chart_generator.py
git commit -m "feat: add chart generator — chart_spec dict to Plotly figure"
```

---

## Task 4: Claude Agent

**Files:**
- Create: `chatbot/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests (parse logic only — no API calls)**

Create `tests/test_agent.py`:
```python
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
    assert "Revenue" in result["answer"]


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
```

- [ ] **Step 2: Run to confirm failures**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_agent.py -v
```

Expected: all 6 tests FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement agent.py**

Create `chatbot/agent.py`:
```python
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


def ask(ctx: DataContext, messages: list[dict], user_message: str, language: str) -> dict:
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
    return {"answer": answer, "chart_spec": chart_spec, "suggestions": suggestions}
```

- [ ] **Step 4: Run tests — expect PASS**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_agent.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```
git add chatbot/agent.py tests/test_agent.py
git commit -m "feat: add Claude agent with prompt builder and response parser"
```

---

## Task 5: Voice Component

**Files:**
- Create: `chatbot/voice_html/index.html`
- Create: `chatbot/voice_component.py`

No automated tests — this component is browser-only. Manual verification in Task 8.

- [ ] **Step 1: Create the HTML component**

Create `chatbot/voice_html/index.html`:
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { margin: 0; background: transparent; font-family: sans-serif; }
    #micBtn {
      background: #374151; border: none; border-radius: 50%;
      width: 36px; height: 36px; cursor: pointer; font-size: 16px;
      display: flex; align-items: center; justify-content: center;
    }
    #micBtn:hover { background: #4b5563; }
    #micBtn.listening { background: #dc2626; }
    #status { font-size: 11px; color: #9ca3af; margin-left: 8px; }
    .row { display: flex; align-items: center; }
  </style>
</head>
<body>
  <div class="row">
    <button id="micBtn" onclick="startListening()" title="Click to speak">🎤</button>
    <span id="status"></span>
  </div>
  <script>
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let lang = "en-US";

    // Receive lang from Streamlit
    window.addEventListener("message", (e) => {
      if (e.data.type === "streamlit:render" && e.data.args && e.data.args.lang) {
        lang = e.data.args.lang;
      }
    });

    // Signal ready + height
    window.parent.postMessage({ type: "streamlit:componentReady", apiVersion: 1 }, "*");
    window.parent.postMessage({ type: "streamlit:setFrameHeight", height: 44 }, "*");

    function sendValue(val) {
      window.parent.postMessage({ type: "streamlit:setComponentValue", value: val }, "*");
    }

    function startListening() {
      if (!SpeechRecognition) {
        document.getElementById("status").textContent = "Not supported (use Chrome)";
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = lang;
      recognition.continuous = false;
      recognition.interimResults = false;

      const btn = document.getElementById("micBtn");
      const status = document.getElementById("status");

      recognition.onstart = () => {
        btn.textContent = "🔴";
        btn.classList.add("listening");
        status.textContent = "Listening...";
      };
      recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        btn.textContent = "🎤";
        btn.classList.remove("listening");
        status.textContent = "✓ " + text;
        sendValue(text);
      };
      recognition.onerror = () => {
        btn.textContent = "🎤";
        btn.classList.remove("listening");
        status.textContent = "Could not hear — try again";
      };
      recognition.onend = () => {
        btn.textContent = "🎤";
        btn.classList.remove("listening");
      };
      recognition.start();
    }
  </script>
</body>
</html>
```

- [ ] **Step 2: Create voice_component.py**

Create `chatbot/voice_component.py`:
```python
from pathlib import Path
import streamlit.components.v1 as components

_LANG_CODES = {"EN": "en-US", "FR": "fr-FR", "AR": "ar-TN"}

_voice_input = components.declare_component(
    "voice_input",
    path=str(Path(__file__).parent / "voice_html"),
)


def voice_input(language: str = "EN") -> str | None:
    return _voice_input(lang=_LANG_CODES.get(language, "en-US"), default=None)
```

- [ ] **Step 3: Commit**

```
git add chatbot/voice_html/index.html chatbot/voice_component.py
git commit -m "feat: add voice input component using Web Speech API"
```

---

## Task 6: App Skeleton — session state, layout, language switcher

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create app.py with session state and layout**

Create `app.py`:
```python
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(
    page_title="GamefyDB Assistant",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── String translations ────────────────────────────────────────────
STRINGS = {
    "EN": {
        "title": "GamefyDB Assistant",
        "placeholder": "Ask anything about your dashboards...",
        "summary_btn": "📊 Full summary",
        "advice_btn": "💡 Give me advice",
        "anomaly_btn": "⚠️ Any anomalies?",
        "send": "Send",
        "download": "⬇ Download chart",
        "refresh": "🔄 Refresh",
        "no_chart": "Ask a question — a chart will appear here when relevant.",
        "greeting": "Hi! Ask me anything about your gaming center — revenue, members, forecasts, anomalies, or anything else.",
        "anomaly_greeting": "Hi! I noticed **{n} anomaly(ies)** in the past 7 days. Want me to show you?",
    },
    "FR": {
        "title": "Assistant GamefyDB",
        "placeholder": "Posez n'importe quelle question sur vos données...",
        "summary_btn": "📊 Résumé complet",
        "advice_btn": "💡 Conseils",
        "anomaly_btn": "⚠️ Anomalies récentes?",
        "send": "Envoyer",
        "download": "⬇ Télécharger",
        "refresh": "🔄 Actualiser",
        "no_chart": "Posez une question — un graphique apparaîtra ici si pertinent.",
        "greeting": "Bonjour ! Posez-moi n'importe quelle question sur votre gaming center.",
        "anomaly_greeting": "Bonjour ! J'ai détecté **{n} anomalie(s)** ces 7 derniers jours. Voulez-vous voir ?",
    },
    "AR": {
        "title": "مساعد GamefyDB",
        "placeholder": "اسألني أي شيء عن بياناتك...",
        "summary_btn": "📊 ملخص شامل",
        "advice_btn": "💡 نصائح",
        "anomaly_btn": "⚠️ أي شذوذات؟",
        "send": "إرسال",
        "download": "⬇ تحميل",
        "refresh": "🔄 تحديث",
        "no_chart": "اسأل سؤالاً — سيظهر الرسم البياني هنا عند الحاجة.",
        "greeting": "مرحباً! اسألني أي شيء عن بيانات مركز الألعاب.",
        "anomaly_greeting": "مرحباً! لاحظت **{n} شذوذ(ات)** في آخر 7 أيام. هل تريد أن أريك؟",
    },
}

# ── Session state init ─────────────────────────────────────────────
if "language" not in st.session_state:
    st.session_state.language = "EN"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_chart" not in st.session_state:
    st.session_state.current_chart = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "data" not in st.session_state:
    st.session_state.data = None
if "last_chart_spec" not in st.session_state:
    st.session_state.last_chart_spec = None
if "voice_pending" not in st.session_state:
    st.session_state.voice_pending = None

# ── Load data (once) ───────────────────────────────────────────────
@st.cache_resource
def get_data():
    from chatbot.data_loader import load_data, recent_anomaly_count
    ctx = load_data()
    return ctx, recent_anomaly_count(ctx)

ctx, anomaly_count = get_data()
strings = STRINGS[st.session_state.language]

# ── Startup greeting (once) ────────────────────────────────────────
if not st.session_state.messages:
    if anomaly_count > 0:
        greeting = strings["anomaly_greeting"].format(n=anomaly_count)
    else:
        greeting = strings["greeting"]
    st.session_state.messages.append({"role": "assistant", "content": greeting, "chart_spec": None, "suggestions": []})

# ── Top bar ────────────────────────────────────────────────────────
top_left, top_right = st.columns([3, 1])
with top_left:
    st.markdown(f"### 🎮 {strings['title']}")
with top_right:
    lang_col1, lang_col2, lang_col3, badge_col = st.columns([1, 1, 1, 2])
    with lang_col1:
        if st.button("EN", key="lang_en", type="primary" if st.session_state.language == "EN" else "secondary"):
            st.session_state.language = "EN"
            st.rerun()
    with lang_col2:
        if st.button("FR", key="lang_fr", type="primary" if st.session_state.language == "FR" else "secondary"):
            st.session_state.language = "FR"
            st.rerun()
    with lang_col3:
        if st.button("AR", key="lang_ar", type="primary" if st.session_state.language == "AR" else "secondary"):
            st.session_state.language = "AR"
            st.rerun()
    with badge_col:
        st.markdown("👤 **Owner**")

st.divider()

# ── Main layout ────────────────────────────────────────────────────
col_chat, col_chart = st.columns([1, 1.3])
```

- [ ] **Step 2: Verify it starts without errors**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open http://localhost:8501 — should show the top bar with language buttons and a divider. No errors in terminal.

- [ ] **Step 3: Commit**

```
git add app.py
git commit -m "feat: app skeleton — session state, layout, language switcher, top bar"
```

---

## Task 7: Chat Panel — conversation, input, quick actions, send logic

**Files:**
- Modify: `app.py` (append to bottom)

- [ ] **Step 1: Append chat panel code to app.py**

Add this to the bottom of `app.py`:
```python
# ── Chat panel (left column) ───────────────────────────────────────
with col_chat:
    # Conversation history
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])
                # Suggestion chips after assistant messages
                if msg["role"] == "assistant" and msg.get("suggestions"):
                    for i, sugg in enumerate(msg["suggestions"]):
                        if st.button(sugg, key=f"sugg_{id(msg)}_{i}"):
                            st.session_state.voice_pending = sugg
                            st.rerun()

    # Quick action buttons
    qa_col1, qa_col2, qa_col3 = st.columns(3)
    with qa_col1:
        if st.button(strings["summary_btn"], use_container_width=True):
            st.session_state.voice_pending = "Give me a full summary of everything"
            st.rerun()
    with qa_col2:
        if st.button(strings["advice_btn"], use_container_width=True):
            st.session_state.voice_pending = "What should I focus on improving?"
            st.rerun()
    with qa_col3:
        if st.button(strings["anomaly_btn"], use_container_width=True):
            st.session_state.voice_pending = "Show me recent anomalies"
            st.rerun()

    # Voice + text input row
    voice_col, input_col, send_col = st.columns([1, 6, 2])
    with voice_col:
        from chatbot.voice_component import voice_input
        transcript = voice_input(language=st.session_state.language)
        if transcript and transcript != st.session_state.get("_last_transcript"):
            st.session_state["_last_transcript"] = transcript
            st.session_state.voice_pending = transcript
            st.rerun()

    with input_col:
        user_text = st.text_input(
            "",
            value=st.session_state.voice_pending or "",
            placeholder=strings["placeholder"],
            label_visibility="collapsed",
            key="user_input_field",
        )
    with send_col:
        send_clicked = st.button(strings["send"], type="primary", use_container_width=True)

    # Handle send
    query = None
    if send_clicked and user_text.strip():
        query = user_text.strip()
    elif st.session_state.voice_pending and not user_text.strip():
        query = st.session_state.voice_pending

    if query:
        st.session_state.voice_pending = None
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query, "chart_spec": None, "suggestions": []})
        # Call agent
        from chatbot.agent import ask
        with st.spinner("Thinking..."):
            result = ask(ctx, [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]], query, st.session_state.language)
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "chart_spec": result["chart_spec"],
            "suggestions": result["suggestions"],
        })
        # Update chart
        if result["chart_spec"]:
            from chatbot.chart_generator import make_chart
            st.session_state.current_chart = make_chart(result["chart_spec"], ctx.tables)
            st.session_state.last_chart_spec = result["chart_spec"]
        st.rerun()
```

- [ ] **Step 2: Test manually**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open http://localhost:8501. Verify:
- Greeting message appears in chat
- Typing in the input box and clicking Send shows user + bot messages
- Quick action buttons trigger a message
- Language switcher changes button labels

- [ ] **Step 3: Commit**

```
git add app.py
git commit -m "feat: chat panel — conversation rendering, input, quick actions, send logic"
```

---

## Task 8: Chart Panel — display, download, refresh

**Files:**
- Modify: `app.py` (append to bottom)

- [ ] **Step 1: Append chart panel code to app.py**

Add this to the bottom of `app.py`:
```python
# ── Chart panel (right column) ────────────────────────────────────
with col_chart:
    st.markdown("**Chart**")
    if st.session_state.current_chart is not None:
        st.plotly_chart(st.session_state.current_chart, use_container_width=True)

        # Action buttons
        dl_col, ref_col = st.columns(2)
        with dl_col:
            chart_html = st.session_state.current_chart.to_html(full_html=True, include_plotlyjs="cdn")
            st.download_button(
                label=strings["download"],
                data=chart_html,
                file_name="gamefydb_chart.html",
                mime="text/html",
                use_container_width=True,
            )
        with ref_col:
            if st.button(strings["refresh"], use_container_width=True):
                if st.session_state.last_chart_spec:
                    from chatbot.chart_generator import make_chart
                    st.session_state.current_chart = make_chart(st.session_state.last_chart_spec, ctx.tables)
                    st.rerun()
    else:
        st.markdown(
            f"""<div style="display:flex;align-items:center;justify-content:center;
            height:300px;color:#64748b;font-size:14px;text-align:center;
            background:#1e293b;border-radius:8px;padding:2rem;">
            {strings['no_chart']}
            </div>""",
            unsafe_allow_html=True,
        )
```

- [ ] **Step 2: Test manually**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open http://localhost:8501 and ask: *"Show me revenue over time as a line chart"*. Verify:
- A Plotly chart appears in the right panel
- "Download chart" button downloads an HTML file that opens in browser
- "Refresh" button re-renders the same chart

- [ ] **Step 3: Commit**

```
git add app.py
git commit -m "feat: chart panel — Plotly display, HTML download, refresh button"
```

---

## Task 9: Final test pass + run all tests

**Files:**
- No new files

- [ ] **Step 1: Run the full test suite**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py -v
```

Expected output:
```
tests/test_data_loader.py::test_build_schemas_includes_all_keys PASSED
tests/test_data_loader.py::test_build_summary_includes_revenue PASSED
tests/test_data_loader.py::test_build_summary_includes_member_count PASSED
tests/test_data_loader.py::test_recent_anomaly_count_today PASSED
tests/test_data_loader.py::test_recent_anomaly_count_no_anomalies_table PASSED
tests/test_data_loader.py::test_load_data_skips_missing_files PASSED
tests/test_chart_generator.py::test_bar_chart_returns_figure PASSED
tests/test_chart_generator.py::test_line_chart_returns_figure PASSED
tests/test_chart_generator.py::test_filter_is_applied PASSED
tests/test_chart_generator.py::test_missing_source_returns_none PASSED
tests/test_chart_generator.py::test_bad_column_returns_none PASSED
tests/test_chart_generator.py::test_malformed_spec_returns_none PASSED
tests/test_agent.py::test_parse_answer_only PASSED
tests/test_agent.py::test_parse_chart_spec PASSED
tests/test_agent.py::test_parse_suggestions PASSED
tests/test_agent.py::test_parse_malformed_json_is_safe PASSED
tests/test_agent.py::test_system_prompt_contains_language_instruction PASSED
tests/test_agent.py::test_system_prompt_contains_data_summary PASSED

18 passed
```

- [ ] **Step 2: End-to-end smoke test**

Double-click `launch.bat`. Verify all of these work:
- App opens at http://localhost:8501
- Proactive message shows if anomalies exist in last 7 days
- Language buttons switch UI labels
- "📊 Full summary" button returns a text summary from Claude
- "⚠️ Any anomalies?" shows anomaly info
- Asking "show me revenue by day as a bar chart" produces a chart on the right
- Download button downloads a working HTML chart
- Voice mic button works in Chrome (click, speak, text appears in input)
- Asking follow-up like "now show it as a line chart" works (conversation memory)

- [ ] **Step 3: Final commit**

```
git add .
git commit -m "feat: complete GamefyDB dashboard assistant — chat, charts, voice, multilingual"
```
