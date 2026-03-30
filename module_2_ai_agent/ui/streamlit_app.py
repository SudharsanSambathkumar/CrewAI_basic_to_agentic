"""
Module 2 — Complaint Intelligence System
ui/streamlit_app.py

Inspired by: "Complaint tone escalation detector"
Use case: Bank/e-commerce support team — classify incoming complaints by
issue type AND emotional temperature, then auto-generate routing + response strategy.
"""

import streamlit as st
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.crew import run

st.set_page_config(
    page_title="Module 2 · Complaint Intelligence",
    page_icon="🎯",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');
.mod-badge {
    display:inline-block; background:#1a0f2e; color:#a78bfa;
    padding:3px 14px; border-radius:20px; font-size:0.72rem;
    font-weight:700; letter-spacing:0.07em; font-family:'JetBrains Mono',monospace;
    margin-bottom:0.4rem;
}
.temp-calm      { background:#d1fae5; color:#065f46; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; }
.temp-frustrated{ background:#fef9c3; color:#713f12; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; }
.temp-angry     { background:#fee2e2; color:#991b1b; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; }
.temp-threat    { background:#fecaca; color:#7f1d1d; padding:3px 12px; border-radius:12px; font-weight:800; font-size:0.8rem; }
.temp-churn     { background:#ffedd5; color:#7c2d12; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; }
.temp-pr        { background:#fce7f3; color:#831843; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; }
.panel {
    background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
    padding:1.1rem 1.3rem; font-size:0.9rem; line-height:1.75;
    white-space:pre-wrap;
}
.panel-blue  { border-left:4px solid #3b82f6; }
.panel-green { border-left:4px solid #22c55e; }
.agent-label { font-size:0.72rem; font-weight:700; text-transform:uppercase;
               letter-spacing:0.06em; margin-bottom:6px; font-family:'JetBrains Mono',monospace; }
.a1 { color:#1d4ed8; } .a2 { color:#15803d; }
.timing { color:#94a3b8; font-size:0.73rem; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown('<div class="mod-badge">MODULE 2 · AI AGENT · BFSI USE CASE</div>', unsafe_allow_html=True)
st.title("🎯 Complaint Intelligence System")
st.caption("**2 Agents** · Analyst → Strategist · Gemini 2.5 Flash")

with st.expander("📚 Use case + CrewAI concepts", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Use Case**")
        st.markdown(
            "Inspired by *complaint tone escalation detection* in banking. "
            "Every incoming complaint is classified by **issue type AND emotional temperature**, "
            "then routed with a specific response strategy — not a generic template."
        )
    with c2:
        st.markdown("**CrewAI Concept: `context=[task]`**")
        st.code("""
# Agent 2 reads Agent 1's output automatically
strategy_task = Task(
    ...,
    context=[analysis_task]  # ← key line
)""", language="python")
        st.caption("Zero manual passing. CrewAI injects it.")

st.divider()

# ── Sample complaints ──────────────────────────────────────────
SAMPLES = {
    "🔴 High-temp: EMI double charge + RBI threat": (
        "I have been charged twice for my EMI this month and nobody is picking up the phone. "
        "This is absolutely unacceptable. I am going to file a complaint with RBI and "
        "the Banking Ombudsman if this is not resolved TODAY. I have been your customer "
        "for 8 years and this is how you treat me.",
        "Phone"
    ),
    "🟡 Mid-temp: Account frozen, rent due tomorrow": (
        "Your bank froze my account without any notice. I have my salary credited in there "
        "and I cannot access a single rupee. My rent payment is due tomorrow. "
        "I am posting about this on Twitter right now if someone doesn't call me back.",
        "Twitter/X"
    ),
    "🟢 Low-temp: Statement query": (
        "Hi, I think there might be a small discrepancy in my November statement. "
        "Could someone please take a look when you get a chance? No rush.",
        "Email"
    ),
    "🔴 Fraud alert: Unauthorised transaction": (
        "There is a transaction of Rs 45,000 on my credit card that I did not make. "
        "It happened at 3am this morning from a merchant I have never heard of. "
        "I want this reversed immediately and my card blocked. If this is not done "
        "in the next hour I am going to the police and filing a cybercrime complaint.",
        "Mobile App"
    ),
}

CHANNELS = ["Email", "WhatsApp", "Phone", "Twitter/X", "Branch Walk-in", "Mobile App"]

# ── Session state ──────────────────────────────────────────────
if "m2_history" not in st.session_state:
    st.session_state.m2_history = []

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Setup")
    st.code("GCP_PROJECT_ID=your-project-id\nGCP_LOCATION=us-central1", language="bash")
    st.divider()

    st.markdown("**Pipeline**")
    st.code("""Complaint + Channel
       │
       ▼
Agent 1: Analyst (0.2)
  → Issue Category
  → Emotional Temperature
  → Risk Flags
       │ context=[analysis_task]
       ▼
Agent 2: Strategist (0.6)
  → Routing Decision
  → SLA
  → Draft Response""", language="text")

    st.divider()
    st.markdown("**Speed fixes**")
    st.markdown("✅ Lazy `vertexai.init()`")
    st.markdown("✅ `@lru_cache` on LLM")
    st.markdown("✅ `streaming=True`")

    st.divider()
    if st.button("🗑 Clear history", use_container_width=True):
        st.session_state.m2_history = []
        st.rerun()

# ── Sample selector ────────────────────────────────────────────
st.subheader("Try a sample or enter your own")
selected_sample = st.selectbox("Load a sample complaint:", ["— enter your own —"] + list(SAMPLES.keys()))

col_complaint, col_channel = st.columns([3, 1])
with col_complaint:
    if selected_sample != "— enter your own —":
        default_text, default_channel = SAMPLES[selected_sample]
    else:
        default_text, default_channel = "", "Email"

    complaint_text = st.text_area(
        "Customer complaint:",
        value=default_text,
        height=120,
        placeholder="Paste or type the customer's message here...",
    )

with col_channel:
    channel = st.selectbox(
        "Received via:",
        CHANNELS,
        index=CHANNELS.index(default_channel) if default_channel in CHANNELS else 0,
    )

run_btn = st.button("▶  Analyse Complaint", type="primary", use_container_width=True)

# ── Render history ─────────────────────────────────────────────
for item in st.session_state.m2_history:
    with st.expander(f"📨 [{item['channel']}] {item['complaint'][:80]}...", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="agent-label a1">Agent 1 · Analyst</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel panel-blue">{item["analysis"]}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="agent-label a2">Agent 2 · Strategist</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel panel-green">{item["strategy"]}</div>', unsafe_allow_html=True)

# ── Execution ──────────────────────────────────────────────────
if run_btn:
    if not complaint_text.strip():
        st.warning("⚠️ Please enter a complaint first.")
        st.stop()

    st.divider()
    s1 = st.empty()
    s2 = st.empty()

    s1.markdown("⚙️ **Agent 1 (Analyst)** — classifying issue, temperature, risks...")
    s2.markdown("⏳ **Agent 2 (Strategist)** — waiting for analysis...")

    try:
        t0 = time.time()
        result = run(complaint_text.strip(), channel)
        elapsed = round(time.time() - t0, 1)

        s1.empty(); s2.empty()
        st.success(f"✅ Analysis complete in {elapsed}s")

        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown('<div class="agent-label a1">🔍 Agent 1 · Complaint Analyst (temp=0.2)</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel panel-blue">{result["analysis"]}</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="agent-label a2">📋 Agent 2 · Response Strategist (temp=0.6)</div>', unsafe_allow_html=True)
            # Stream word-by-word
            words = result["strategy"].split()
            streamed = ""
            out = st.empty()
            for i, w in enumerate(words):
                streamed += w + " "
                if i % 8 == 0:
                    out.markdown(f'<div class="panel panel-green">{streamed}▌</div>', unsafe_allow_html=True)
                    time.sleep(0.007)
            out.markdown(f'<div class="panel panel-green">{result["strategy"]}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="timing">⚡ {elapsed}s · channel: {channel}</div>', unsafe_allow_html=True)

        st.session_state.m2_history.insert(0, {
            "complaint": complaint_text.strip(),
            "channel":   channel,
            "analysis":  result["analysis"],
            "strategy":  result["strategy"],
        })

    except Exception as e:
        s1.empty(); s2.empty()
        st.error(f"❌ {e}")
