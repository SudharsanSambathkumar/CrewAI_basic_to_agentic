"""
Module 3 — Loan Narrative Builder (Agentic AI)
ui/streamlit_app.py

Use Case: Thin-file loan applicant credit assessment using alternative data.
Inspired by: "Loan story builder" + "KYC discrepancy detective" from BFSI.
"""

import streamlit as st
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.fast_crew import run as fast_run
from app.crew import run as full_run

st.set_page_config(
    page_title="Module 3 · Loan Narrative Builder",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&display=swap');
.mod-badge {
    display:inline-block; background:#0c1a2e; color:#38bdf8;
    padding:3px 14px; border-radius:20px; font-size:0.72rem;
    font-weight:700; letter-spacing:0.07em; font-family:'JetBrains Mono',monospace;
    margin-bottom:0.4rem;
}
.panel {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-radius:10px; padding:1.1rem 1.3rem;
    font-size:0.88rem; line-height:1.75; white-space:pre-wrap;
}
.p1 { border-left:4px solid #3b82f6; }
.p2 { border-left:4px solid #8b5cf6; }
.p3r{ border-left:4px solid #22c55e; }
.p3y{ border-left:4px solid #f59e0b; }
.p3x{ border-left:4px solid #ef4444; }
.agent-label {
    font-size:0.72rem; font-weight:700; text-transform:uppercase;
    letter-spacing:0.06em; margin-bottom:6px;
    font-family:'JetBrains Mono',monospace;
}
.a1{color:#1d4ed8;} .a2{color:#6d28d9;} .a3{color:#15803d;}
.timing{color:#94a3b8;font-size:0.73rem;margin-top:4px;}
.field-label{font-size:0.78rem;font-weight:600;color:#475569;margin-bottom:2px;}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown('<div class="mod-badge">MODULE 3 · AGENTIC AI · BFSI USE CASE</div>', unsafe_allow_html=True)
st.title("🏦 Loan Narrative Builder")
st.caption("**3 Agents** · Alt-Data Analyst → Narrative Writer → Risk Reviewer · Gemini 2.5 Flash")

with st.expander("📚 Use case + CrewAI concepts", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Use Case**")
        st.markdown(
            "Inspired by *loan story builder* in BFSI. "
            "Thin-file customers — no CIBIL score, no formal credit history — "
            "are assessed using **alternative data**: rent payments, utility bills, "
            "UPI activity, employment tenure. Three agents build a complete "
            "credit narrative and risk-adjusted loan recommendation."
        )
    with c2:
        st.markdown("**CrewAI: Chained context**")
        st.code("""# Task 2 reads Task 1
narrative_task = Task(
  context=[alt_data_task]
)
# Task 3 reads BOTH
review_task = Task(
  context=[alt_data_task,
           narrative_task]
)""", language="python")
        st.caption("Reviewer sees raw signals AND narrative — catches inconsistencies autonomously.")

st.divider()

# ── Sample profiles ────────────────────────────────────────────
SAMPLES = {
    "Ravi Kumar — NTC vegetable vendor": {
        "applicant_name": "Ravi Kumar",
        "loan_purpose": "Purchase a refrigerated cart to expand into dairy products",
        "loan_amount": "₹75,000",
        "occupation": "Self-employed vegetable vendor, 6 years",
        "monthly_rent_paid": "₹8,500/month for 4 years — zero missed payments",
        "electricity_bill": "Regular payer, ₹1,200-1,800/month for 3 years",
        "mobile_recharge": "₹299/month prepaid, consistent for 5 years",
        "upi_transactions": "~40 transactions/month, avg ticket ₹350",
        "bank_savings_balance": "₹12,000 average monthly balance",
        "cibil_score": "No score (NTC)",
        "existing_loans": "None",
        "employment_stability": "Same location, same trade for 6 years",
        "family": "Married, 2 school-going children",
        "references": "Shop landlord (4 yr tenancy, no issues), neighbour vendor",
    },
    "Priya Menon — Gig worker, food delivery": {
        "applicant_name": "Priya Menon",
        "loan_purpose": "Purchase a second-hand two-wheeler to increase delivery capacity",
        "loan_amount": "₹45,000",
        "occupation": "Food delivery partner (Swiggy + Zomato), 2.5 years",
        "monthly_rent_paid": "₹6,000/month for 2 years — 1 delayed payment (COVID period)",
        "electricity_bill": "Shared accommodation, not in her name",
        "mobile_recharge": "₹399/month postpaid, 3 years",
        "upi_transactions": "~80 transactions/month (delivery earnings + personal)",
        "platform_earnings": "₹22,000-28,000/month average (last 6 months)",
        "bank_savings_balance": "₹8,500 average monthly balance",
        "cibil_score": "Score: 0 (no credit products ever taken)",
        "existing_loans": "None",
        "employment_stability": "Active on 2 platforms, consistent ratings above 4.5",
        "family": "Single, living with roommate",
    },
}

# ── Session state ──────────────────────────────────────────────
if "m3_history" not in st.session_state:
    st.session_state.m3_history = []

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Setup")
    st.code("GCP_PROJECT_ID=your-project-id\nGCP_LOCATION=us-central1", language="bash")
    st.divider()
    st.markdown("**Pipeline**")
    st.code("""Alt-Data Input
     │
     ▼
Agent 1: Analyst (0.3)
  → Structured signals
     │ context=[alt_task]
     ▼
Agent 2: Writer (0.7)
  → Credit narrative
     │ context=[alt_task,
     │          narrative_task]
     ▼
Agent 3: Reviewer (0.4)
  → Risk assessment
  → Loan parameters
  → APPROVE / DECLINE""", language="text")
    st.divider()
    st.markdown("**Speed fixes**")
    st.markdown("✅ Lazy `vertexai.init()`")
    st.markdown("✅ `@lru_cache` — 3 temps")
    st.markdown("✅ `streaming=True`")
    st.divider()
    st.markdown("**Execution Mode**")
    fast_mode = st.toggle("⚡ Fast Mode (1 call ~20s)", value=True)
    if fast_mode:
        st.caption("1 LLM call · Same output · Much faster")
    else:
        st.caption("3 CrewAI agents · Sequential · ~100s · Teaches multi-agent flow")

    st.divider()
    if st.button("🗑 Clear history", use_container_width=True):
        st.session_state.m3_history = []
        st.rerun()

# ── Sample selector ────────────────────────────────────────────
st.subheader("Load a sample applicant or enter your own")
selected = st.selectbox("Sample profile:", ["— enter manually —"] + list(SAMPLES.keys()))

if selected != "— enter manually —":
    sample = SAMPLES[selected]
else:
    sample = {}

# ── Applicant form ─────────────────────────────────────────────
with st.form("applicant_form"):
    st.markdown("**Applicant Details**")
    col1, col2, col3 = st.columns(3)
    with col1:
        applicant_name = st.text_input("Applicant name", value=sample.get("applicant_name", ""))
        loan_purpose   = st.text_input("Loan purpose", value=sample.get("loan_purpose", ""))
    with col2:
        loan_amount = st.text_input("Loan amount requested", value=sample.get("loan_amount", ""))
        occupation  = st.text_input("Occupation / Business", value=sample.get("occupation", ""))
    with col3:
        cibil = st.text_input("CIBIL / Credit score", value=sample.get("cibil_score", "NTC"))
        existing = st.text_input("Existing loans", value=sample.get("existing_loans", "None"))

    st.markdown("**Alternative Data Signals**")
    col4, col5 = st.columns(2)
    with col4:
        rent    = st.text_input("Rent payment history", value=sample.get("monthly_rent_paid", ""))
        utility = st.text_input("Utility bill history", value=sample.get("electricity_bill", ""))
        mobile  = st.text_input("Mobile recharge pattern", value=sample.get("mobile_recharge", ""))
        upi     = st.text_input("UPI transaction activity", value=sample.get("upi_transactions", ""))
    with col5:
        savings    = st.text_input("Bank/savings balance", value=sample.get("bank_savings_balance", ""))
        employment = st.text_input("Employment stability", value=sample.get("employment_stability", ""))
        family     = st.text_input("Family profile", value=sample.get("family", ""))
        references = st.text_input("References / co-signers", value=sample.get("references", ""))

    extra = st.text_area("Additional data points (optional)",
                          value=sample.get("platform_earnings", ""),
                          height=60,
                          placeholder="Platform earnings, GST returns, property ownership, etc.")

    submitted = st.form_submit_button("▶  Run 3-Agent Credit Assessment", type="primary", use_container_width=True)

# ── Render history ─────────────────────────────────────────────
for item in st.session_state.m3_history:
    with st.expander(f"🏦 {item['name']} — {item['amount']} — {item['purpose'][:50]}", expanded=False):
        t1, t2, t3 = st.tabs(["📊 Signals", "📝 Narrative", "✅ Review & Decision"])
        with t1:
            st.markdown(f'<div class="panel p1">{item["signals"]}</div>', unsafe_allow_html=True)
        with t2:
            st.markdown(f'<div class="panel p2">{item["narrative"]}</div>', unsafe_allow_html=True)
        with t3:
            st.markdown(f'<div class="panel p3r">{item["review"]}</div>', unsafe_allow_html=True)

# ── Execution ──────────────────────────────────────────────────
if submitted:
    if not applicant_name.strip() or not loan_amount.strip():
        st.warning("⚠️ Applicant name and loan amount are required.")
        st.stop()

    applicant_data = {
        "Occupation": occupation,
        "CIBIL Score": cibil,
        "Existing Loans": existing,
        "Rent Payment History": rent,
        "Utility Bill History": utility,
        "Mobile Recharge": mobile,
        "UPI Activity": upi,
        "Bank/Savings Balance": savings,
        "Employment Stability": employment,
        "Family Profile": family,
        "References": references,
    }
    if extra.strip():
        applicant_data["Additional Data"] = extra

    # Remove empty fields
    applicant_data = {k: v for k, v in applicant_data.items() if v.strip()}

    st.divider()
    s1 = st.empty()
    s2 = st.empty()
    s3 = st.empty()

    def upd(a1, a2, a3):
        icons = ["⚙️", "⏳"]
        s1.markdown(f"{'⚙️' if a1==0 else '✅'} **Agent 1 (Alt-Data Analyst)** — extracting credit signals...")
        s2.markdown(f"{'⚙️' if a2==0 else ('✅' if a2==1 else '⏳')} **Agent 2 (Narrative Writer)** — building credit story...")
        s3.markdown(f"{'⚙️' if a3==0 else '⏳'} **Agent 3 (Risk Reviewer)** — reviewing & recommending...")

    upd(0, -1, -1)

    try:
        t0 = time.time()
        run_fn = fast_run if fast_mode else full_run
        spinner_msg = "⚡ Fast mode — 1 LLM call..." if fast_mode else "⚙️ Full CrewAI — 3 agents..."
        with st.spinner(spinner_msg):
            result = run_fn(
                applicant_data=applicant_data,
                applicant_name=applicant_name.strip(),
                loan_purpose=loan_purpose.strip(),
                loan_amount=loan_amount.strip(),
            )
        elapsed = round(time.time() - t0, 1)

        s1.empty(); s2.empty(); s3.empty()
        st.success(f"✅ Assessment complete in {elapsed}s")

        tab1, tab2, tab3 = st.tabs([
            "📊 Alt-Data Signals",
            "📝 Credit Narrative",
            "✅ Risk Review & Decision",
        ])

        with tab1:
            st.markdown('<div class="agent-label a1">Agent 1 · Alt-Data Analyst (temp=0.3) — forensic extraction</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel p1">{result["signals"]}</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="agent-label a2">Agent 2 · Credit Narrative Officer (temp=0.7) — reads Agent 1 via context=[alt_task]</div>', unsafe_allow_html=True)
            # Stream narrative word by word
            words = result["narrative"].split()
            streamed = ""
            out = st.empty()
            for i, w in enumerate(words):
                streamed += w + " "
                if i % 8 == 0:
                    out.markdown(f'<div class="panel p2">{streamed}▌</div>', unsafe_allow_html=True)
                    time.sleep(0.007)
            out.markdown(f'<div class="panel p2">{result["narrative"]}</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="agent-label a3">Agent 3 · Risk Reviewer (temp=0.4) — reads BOTH agents via context=[alt_task, narrative_task]</div>', unsafe_allow_html=True)
            # Colour the panel based on decision keyword
            rv = result["review"]
            panel_class = "p3r" if "APPROVE" in rv.upper() and "DECLINE" not in rv.upper() else \
                          "p3x" if "DECLINE" in rv.upper() else "p3y"
            st.markdown(f'<div class="panel {panel_class}">{rv}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="timing">⚡ {elapsed}s total for 3 agents</div>', unsafe_allow_html=True)

        st.session_state.m3_history.insert(0, {
            "name":      applicant_name,
            "amount":    loan_amount,
            "purpose":   loan_purpose,
            "signals":   result["signals"],
            "narrative": result["narrative"],
            "review":    result["review"],
        })

    except Exception as e:
        s1.empty(); s2.empty(); s3.empty()
        st.error(f"❌ {e}")
