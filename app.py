import streamlit as st
from dotenv import load_dotenv

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
        "thinking": "Thinking...",
        "error": "Sorry, something went wrong: {e}",
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
        "thinking": "En train de réfléchir...",
        "error": "Désolé, une erreur s'est produite : {e}",
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
        "thinking": "جارٍ التفكير...",
        "error": "عذراً، حدث خطأ ما: {e}",
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

# ── Chat panel (left column) ───────────────────────────────────────
with col_chat:
    # Conversation history
    chat_container = st.container(height=400)
    with chat_container:
        for msg_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])
                # Suggestion chips after assistant messages
                if msg["role"] == "assistant" and msg.get("suggestions"):
                    for i, sugg in enumerate(msg["suggestions"]):
                        if st.button(sugg, key=f"sugg_{msg_idx}_{i}"):
                            st.session_state.voice_pending = sugg
                            st.rerun()

    # Quick action buttons
    qa_col1, qa_col2, qa_col3 = st.columns(3)
    with qa_col1:
        if st.button(strings["summary_btn"], key="qa_summary", use_container_width=True):
            st.session_state.voice_pending = "Give me a full summary of everything"
            st.rerun()
    with qa_col2:
        if st.button(strings["advice_btn"], key="qa_advice", use_container_width=True):
            st.session_state.voice_pending = "What should I focus on improving?"
            st.rerun()
    with qa_col3:
        if st.button(strings["anomaly_btn"], key="qa_anomaly", use_container_width=True):
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
        if st.session_state.voice_pending:
            st.session_state["user_input_field"] = st.session_state.voice_pending
        user_text = st.text_input(
            "",
            placeholder=strings["placeholder"],
            label_visibility="collapsed",
            key="user_input_field",
        )
        if st.session_state.voice_pending and user_text == st.session_state.voice_pending:
            st.session_state.voice_pending = None
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
        st.session_state.messages.append({"role": "user", "content": query, "chart_spec": None, "suggestions": []})
        from chatbot.agent import ask
        try:
            with st.spinner(strings["thinking"]):
                result = ask(ctx, [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]], query, st.session_state.language)
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": strings["error"].format(e=e),
                "chart_spec": None,
                "suggestions": [],
            })
            st.rerun()
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "chart_spec": result["chart_spec"],
                "suggestions": result["suggestions"],
            })
            if result["chart_spec"]:
                from chatbot.chart_generator import make_chart
                st.session_state.current_chart = make_chart(result["chart_spec"], ctx.tables)
                st.session_state.last_chart_spec = result["chart_spec"]
            st.rerun()
