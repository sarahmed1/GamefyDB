# Finish Dashboard Chatbot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining gaps in the GamefyDB Dashboard Assistant — wire in voice input, fix the brittle `voice_pending` → text-input handoff, and run an end-to-end smoke test.

**Architecture:** Three narrow changes to `app.py` only. No changes to `chatbot/agent.py` (Gemini API code stays untouched). No new files. The 18 existing unit tests must keep passing.

**Tech Stack:** Streamlit (session state), Plotly, Web Speech API via the existing `chatbot.voice_component`.

**Python path (use this for all commands):**
`C:/Users/sarah/AppData/Local/Python/bin/python`

---

## File Map

| File | Change |
|------|--------|
| `app.py` | Refactor `voice_pending` flow; add `voice_col` and voice handler in the chat panel |

No new files. No test files touched. Reference spec: `docs/superpowers/specs/2026-05-14-chatbot-finish-design.md`.

---

## Task 1: Refactor voice_pending → chat_input_value state flow

The current code in `app.py:152-163` mutates `st.session_state["user_input_field"]` directly and uses a brittle equality check to clear `voice_pending`. Replace with a clean pattern where `voice_pending` is a one-shot signal that gets copied into a dedicated input-value key, then cleared immediately.

**Files:**
- Modify: `app.py:64-75` (session state init)
- Modify: `app.py:152-172` (input row + send-handling logic)

- [ ] **Step 1: Add `chat_input_value` to session state init**

Open `app.py`. Find the session state init block (currently around line 64-75 — contains `if "language" not in st.session_state:` through `if "voice_pending" not in st.session_state:`).

After the `voice_pending` init, add:

```python
if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""
if "_last_transcript" not in st.session_state:
    st.session_state._last_transcript = None
```

- [ ] **Step 2: Apply `voice_pending` before rendering the text input**

Find the "Input row" block (currently `app.py:152` onwards: `input_col, send_col = st.columns([6, 2])`).

Replace the entire block from `# Input row` through the `with send_col:` block (about lines 151-165) with:

```python
    # Promote a pending value (from voice, suggestion chip, or quick action)
    # into the input field BEFORE the widget is rendered, then clear the signal.
    if st.session_state.voice_pending is not None:
        st.session_state.chat_input_value = st.session_state.voice_pending
        st.session_state.voice_pending = None

    # Input row
    input_col, send_col = st.columns([6, 2])
    with input_col:
        user_text = st.text_input(
            "",
            value=st.session_state.chat_input_value,
            placeholder=strings["placeholder"],
            label_visibility="collapsed",
            key="user_input_field",
        )
    with send_col:
        send_clicked = st.button(strings["send"], type="primary", use_container_width=True)
```

Note: Task 2 will insert `voice_col` into the `st.columns(...)` line — leave it at `[6, 2]` for now.

- [ ] **Step 3: Simplify the send handler**

Find the `# Handle send` block (currently around `app.py:167-172`). Replace it with:

```python
    # Handle send
    query = None
    if send_clicked and user_text.strip():
        query = user_text.strip()
        st.session_state.chat_input_value = ""
```

(Removes the dead `elif st.session_state.voice_pending and not user_text.strip():` branch — `voice_pending` is now consumed before the widget renders, so it can't reach this point.)

Also remove the line `st.session_state.voice_pending = None` from inside the `if query:` block (currently `app.py:175`) — it's a no-op now.

- [ ] **Step 4: Verify existing tests still pass**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py -v
```

Expected: `18 passed`.

- [ ] **Step 5: Smoke-check the app starts without errors**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open `http://localhost:8501`. Verify:
- App loads, greeting appears
- Typing in the input box works
- Clicking a suggestion chip populates the input (does NOT lose typed text on re-render)
- Clicking a quick action button populates the input
- Pressing Send sends the message and clears the input

Stop the server with Ctrl+C.

- [ ] **Step 6: Commit**

```
git add app.py
git commit -m "fix: clean voice_pending -> chat_input_value flow in app.py"
```

---

## Task 2: Wire voice input into the chat panel

The voice component is built (`chatbot/voice_component.py` + `chatbot/voice_html/index.html`) but never imported. Add the import, slot a `voice_col` in front of the text input, and route the transcript through the now-clean `voice_pending` signal.

**Files:**
- Modify: `app.py:1-3` (imports)
- Modify: `app.py` input row (the one just refactored in Task 1)

- [ ] **Step 1: Add the import**

At the top of `app.py`, find the existing imports:

```python
import streamlit as st
from dotenv import load_dotenv
from chatbot.chart_generator import make_chart
```

Append:

```python
from chatbot.voice_component import voice_input
```

- [ ] **Step 2: Add voice_col to the input row**

Find the input row block from Task 1. Change the column split from:

```python
    # Input row
    input_col, send_col = st.columns([6, 2])
```

to:

```python
    # Input row
    voice_col, input_col, send_col = st.columns([1, 5, 2])
    with voice_col:
        transcript = voice_input(language=st.session_state.language)
        if transcript and transcript != st.session_state._last_transcript:
            st.session_state._last_transcript = transcript
            st.session_state.voice_pending = transcript
            st.rerun()
```

Leave the `with input_col:` and `with send_col:` blocks unchanged.

- [ ] **Step 3: Verify existing tests still pass**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py -v
```

Expected: `18 passed`.

- [ ] **Step 4: Smoke-check the mic button appears**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open `http://localhost:8501` **in Chrome or Edge** (Web Speech API does not work in Firefox).

Verify:
- A mic button 🎤 appears to the left of the text input
- Clicking it shows "Listening..." and (after speaking) "✓ <your text>"
- The recognized text lands in the input box and survives a rerun
- Pressing Send sends the spoken query

If the mic button shows "Not supported (use Chrome)", you are not in Chrome/Edge. Switch browsers.

Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```
git add app.py
git commit -m "feat: wire voice input into chatbot UI"
```

---

## Task 3: End-to-end smoke test

Walk through the full feature in a real browser session against the real Gemini backend. Fix anything outside `chatbot/agent.py`. If `agent.py` itself breaks (e.g. invalid model name, auth issue, malformed request), **stop and report** — do not modify it.

**Files:**
- None expected. If a non-agent file needs a fix, modify and commit it under this task with a clear commit message.

- [ ] **Step 1: Preflight — verify `.env` and data files**

Check `.env` exists and contains `GEMINI_API_KEY=...`:

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -c "from dotenv import load_dotenv; load_dotenv(); import os; print('KEY OK' if os.environ.get('GEMINI_API_KEY') else 'MISSING KEY')"
```

Expected: `KEY OK`. If `MISSING KEY`, stop and ask the user to set it.

Check the output CSVs exist (the loader expects them):

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -c "from chatbot.data_loader import load_data; ctx = load_data(); print('Loaded tables:', list(ctx.tables.keys()))"
```

Expected: at least `fact_transaction`, `dim_member`, and ideally `member_loyalty` and `anomalies`. If most are missing, ask the user whether to run `run.py` first.

- [ ] **Step 2: Launch and run the walkthrough in Chrome**

Run:

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m streamlit run app.py
```

Open `http://localhost:8501` in Chrome and verify each step. Note any failure.

**Walkthrough:**

1. **Greeting** — App loads with a greeting message. If `output/forecasts/anomalies.csv` has rows in the last 7 days, the anomaly-variant greeting appears with a count.
2. **Plain Q&A** — Type: `What was total revenue last month?` → Click Send → text answer appears.
3. **Chart generation** — Type: `Show me revenue by day as a bar chart` → bar chart appears in the right panel.
4. **Suggestion chip** — Click any suggestion pill under the last assistant message → it populates the input, then Send fires the question.
5. **Quick action** — Click `📊 Full summary` → response renders.
6. **Language switch** — Click `FR` → UI labels and the next bot reply switch to French. Repeat for `AR`.
7. **Voice input** — Click 🎤, speak a short question (e.g. "show revenue per day") → transcript appears in input → Send.
8. **Chart download** — Click `⬇ Download chart` → an HTML file downloads and opens in a new tab showing the chart.
9. **Refresh** — Click `🔄 Refresh` next to the chart → chart re-renders.

- [ ] **Step 3: Triage failures**

For each failure found in Step 2:

- **Failure outside `chatbot/agent.py`** (Streamlit wiring, chart spec handling, data loader edge case, etc.): debug and fix. Run the 18-test suite after each fix to confirm no regression.
- **Failure inside `chatbot/agent.py`** (Gemini import, model name, request shape, response parsing of real Gemini output): STOP. Report the failure to the user with the exact error message and ask whether to proceed. Do not edit `chatbot/agent.py`.

Common non-agent issues to watch for:
- A `chart_spec` from Gemini referencing a column that doesn't exist → `chart_generator.make_chart` should return `None` gracefully (verify it does; it should, per the test `test_bad_column_returns_none`).
- An anomaly greeting with `{n}` left literal if `recent_anomaly_count` returns 0 but the greeting path was taken — verify the conditional in `app.py:88-93`.

- [ ] **Step 4: Final test run**

```
"C:/Users/sarah/AppData/Local/Python/bin/python" -m pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py -v
```

Expected: `18 passed`.

- [ ] **Step 5: Commit any fixes (only if Step 3 produced any)**

```
git add <files>
git commit -m "fix: <specific issue found during smoke test>"
```

If no fixes were needed, no commit for this task — just note "smoke test passed clean" in the handoff message.

---

## Acceptance Criteria

- All three tasks' commits are on the branch
- `pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py` → `18 passed`
- Smoke-test walkthrough succeeds in Chrome, **or** the only remaining failures are inside `chatbot/agent.py` and have been reported back to the user untouched
