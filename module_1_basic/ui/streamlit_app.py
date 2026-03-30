"""
Module 1 — Basic CrewAI
ui/streamlit_app.py — Session chat UI with word-by-word streaming display.

Run:
    cd module_1_basic_crewai
    streamlit run ui/streamlit_app.py
"""

import streamlit as st
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.crew import run

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Module 1 · Basic CrewAI",
    page_icon="🧱",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
.mod-badge {
    display:inline-block; background:#0f172a; color:#38bdf8;
    padding:3px 14px; border-radius:20px; font-size:0.72rem;
    font-weight:700; letter-spacing:0.07em; font-family:'JetBrains Mono',monospace;
}
.concept-row { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
.cpill {
    background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd;
    padding:3px 11px; border-radius:12px; font-size:0.76rem; font-weight:600;
}
.timing { color:#64748b; font-size:0.75rem; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown('<div class="mod-badge">MODULE 1 · BASIC CREWAI</div>', unsafe_allow_html=True)
st.title("🧱 Basic CrewAI")
st.caption("**1 Agent** · Gemini 2.5 Flash on Vertex AI · Session memory")

with st.expander("📚 What this module teaches", expanded=False):
    st.markdown(
        '<div class="concept-row">'
        '<span class="cpill">Agent</span>'
        '<span class="cpill">Task</span>'
        '<span class="cpill">Crew</span>'
        '<span class="cpill">Process.sequential</span>'
        '<span class="cpill">Session history</span>'
        '</div>', unsafe_allow_html=True
    )
    st.code("""
# The 3 primitives of every CrewAI app:
agent  = Agent(role, goal, backstory, llm)
task   = Task(description, expected_output, agent)
result = Crew(agents=[agent], tasks=[task]).kickoff()
    """, language="python")

st.divider()

# ── Session state: history resets on page reload ──────────────
if "history" not in st.session_state:
    st.session_state.history = []     # list of {role, content}


# ── Render existing chat history ──────────────────────────────
for msg in st.session_state.history:
    avatar = "🧑" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────
prompt = st.chat_input("Ask anything about AI or technology...")

if "_prefill" in st.session_state:
    prompt = st.session_state.pop("_prefill")

if prompt:
    # Add user message to history & display
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    # Run agent
    with st.chat_message("assistant", avatar="🤖"):
        status_box = st.empty()
        status_box.markdown("⏳ *Agent working...*")

        try:
            t0 = time.time()
            # Pass history EXCLUDING the just-added user turn (agent sees it via task)
            context = st.session_state.history[:-1]
            response = run(prompt, history=context)
            elapsed = round(time.time() - t0, 1)

            # Word-by-word streaming display
            words = response.split()
            streamed = ""
            out = st.empty()
            for i, w in enumerate(words):
                streamed += w + " "
                if i % 5 == 0:
                    out.markdown(streamed + "▌")
                    time.sleep(0.01)
            out.markdown(response)
            st.markdown(f'<div class="timing">⚡ {elapsed}s</div>', unsafe_allow_html=True)
            status_box.empty()

        except Exception as e:
            status_box.error(f"❌ {e}")
            response = f"Error: {e}"

    st.session_state.history.append({"role": "assistant", "content": response})
