# Finish Dashboard Chatbot — Design Spec

**Date:** 2026-05-14
**Status:** Approved
**Supersedes:** none — patches gaps left in [2026-05-06-dashboard-chatbot-design.md](2026-05-06-dashboard-chatbot-design.md)

## Context

The 2026-05-06 spec for the GamefyDB Dashboard Assistant is mostly shipped:
data loader, chart generator, Gemini agent, app skeleton, chat panel, and
chart panel all exist and the 18 unit tests pass. Three gaps remain.

## Scope

Three narrow changes. No new files. No changes to `chatbot/agent.py`
(the Gemini API code stays untouched). No test changes — existing tests
must keep passing.

### 1. Wire voice input into `app.py`

`chatbot/voice_component.py` and `chatbot/voice_html/index.html` exist
but are never imported. The original Task 7 in the plan added a
`voice_col` before `input_col`; in the shipped `app.py` that column is
missing.

Change:

- Import `voice_input` from `chatbot.voice_component` at the top of `app.py`.
- Change the input row from `st.columns([6, 2])` →
  `st.columns([1, 5, 2])` for `voice_col, input_col, send_col`.
- In `voice_col`: call `voice_input(language=st.session_state.language)`.
  When the returned transcript differs from `st.session_state._last_transcript`,
  store it on `voice_pending`, update `_last_transcript`, `st.rerun()`.

### 2. Fix `voice_pending` → `user_input_field` flow

Current code (`app.py:154-163`) mutates `st.session_state["user_input_field"]`
directly. Streamlit warns against this and the matching condition that
clears `voice_pending` (`user_text == voice_pending`) is brittle — any
edit to the prefilled text leaves stale state.

Replace with the standard pattern:

- `voice_pending` is the source of truth for "queued text to send".
- The text input uses a dedicated state key for its own value
  (e.g. `chat_input_value`), separate from `voice_pending`.
- When `voice_pending` is set (by mic, suggestion chip, or quick action),
  copy its value into `chat_input_value` once, then clear `voice_pending`.
- Send logic reads from `chat_input_value`.

This makes suggestion chips, quick actions, and voice all behave the same way.

### 3. End-to-end smoke test

Walkthrough on the dev machine in Chrome, with a real `GEMINI_API_KEY`
in `.env` and the `output/` CSVs present:

1. `launch.bat` or `streamlit run app.py` opens the app
2. Greeting message appears (anomaly variant if anomalies in last 7 days)
3. Type "show me revenue by day as a bar chart" → chart appears on right
4. Click a suggestion chip → new question fires
5. Click "📊 Full summary" quick action → response renders
6. Switch EN → FR → AR → labels and greetings update
7. Click mic (Chrome only), say a short phrase → text appears in input

Fix any failure that is **not** inside `chatbot/agent.py`. If the agent
code itself breaks (e.g. model name invalid), stop and report — don't
modify it.

## Out of scope

- Changes to the Gemini API integration (`chatbot/agent.py`)
- New tests (existing 18 must still pass)
- New features beyond the 2026-05-06 spec
- Persistent history, RBAC, deployment — same as parent spec

## Acceptance

- All three changes above are committed
- `pytest tests/test_data_loader.py tests/test_chart_generator.py tests/test_agent.py` shows 18 passed
- Smoke test walkthrough succeeds (or remaining failures are isolated to `chatbot/agent.py` and reported)
