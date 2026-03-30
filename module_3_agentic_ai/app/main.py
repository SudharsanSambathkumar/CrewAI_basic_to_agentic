"""
Module 3 — Loan Narrative Builder
main.py — CLI with MODE selection: Fast (1 call) or Full CrewAI (3 calls).
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

SEP  = "─" * 60
SEP2 = "═" * 60

SAMPLE_APPLICANT = {
    "name": "Ravi Kumar",
    "age": "34",
    "occupation": "Self-employed vegetable vendor, 6 years",
    "monthly_rent_paid": "₹8,500/month for 4 years — zero missed payments",
    "electricity_bill": "Regular payer, ₹1,200-1,800/month for 3 years",
    "mobile_recharge": "₹299/month prepaid, consistent for 5 years",
    "upi_transactions": "~40 transactions/month, avg ticket ₹350",
    "bank_account": "Jan Dhan account, 2 years active",
    "savings_balance": "₹12,000 average monthly balance",
    "family": "Married, 2 children (school-going)",
    "existing_loans": "None",
    "cibil_score": "No score (NTC - New To Credit)",
    "reference_1": "Shop landlord — confirms 4 years tenancy, no issues",
    "reference_2": "Neighbouring vendor — 6 years acquaintance",
    "loan_purpose": "Purchase a refrigerated cart to expand into dairy products",
    "loan_amount_requested": "₹75,000",
}


def main():
    print(SEP2)
    print("  MODULE 3 · Loan Narrative Builder")
    print(SEP2)

    print("\nSelect mode:")
    print("  1. FAST   — 1 LLM call, ~20-30s  (same output, single API call)")
    print("  2. FULL   — 3 CrewAI agents, ~90-120s  (teaches multi-agent flow)")
    mode = input("\nMode (1 or 2, default=1): ").strip() or "1"

    applicant_data = {k: v for k, v in SAMPLE_APPLICANT.items()
                      if k not in ("name", "loan_purpose", "loan_amount_requested")}

    print(f"\n{SEP}")
    if mode == "2":
        print("⚙️  Running FULL 3-agent CrewAI pipeline...")
        print("   Agent 1 → Agent 2 → Agent 3 (sequential)")
        from app.crew import run
    else:
        print("⚡  Running FAST mode — single LLM call...")
        from app.fast_crew import run

    print(f"{SEP}\n")

    t0 = time.time()
    result = run(
        applicant_data=applicant_data,
        applicant_name=SAMPLE_APPLICANT["name"],
        loan_purpose=SAMPLE_APPLICANT["loan_purpose"],
        loan_amount=SAMPLE_APPLICANT["loan_amount_requested"],
    )
    elapsed = round(time.time() - t0, 1)

    print(f"\n{'─'*20} AGENT 1: ALT-DATA SIGNALS {'─'*20}")
    print(result["signals"])

    if result.get("narrative"):
        print(f"\n{'─'*20} AGENT 2: CREDIT NARRATIVE {'─'*20}")
        print(result["narrative"])

    if result.get("review"):
        print(f"\n{'─'*20} AGENT 3: RISK REVIEW & RECOMMENDATION {'─'*5}")
        print(result["review"])

    print(f"\n⚡ {elapsed}s  |  mode: {'FAST (1 call)' if mode != '2' else 'FULL (3 agents)'}\n{SEP}\n")


if __name__ == "__main__":
    main()
