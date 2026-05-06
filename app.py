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
