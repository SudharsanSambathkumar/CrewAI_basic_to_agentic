"""
Module 2 — Complaint Intelligence System
main.py — Standalone CLI. Run independently.

Usage:
    cd module_2_ai_agent
    python app/main.py
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.crew import run

SEP = "─" * 58

SAMPLE_COMPLAINTS = [
    "I have been charged twice for my EMI this month and nobody is picking up the phone. This is absolutely unacceptable. I am going to file a complaint with RBI if this is not resolved TODAY.",
    "Hi, I think there might be a small error in my statement. Could you please check?",
    "Your bank froze my account without any notice. I have salary credited and I cannot access it. I have rent due tomorrow. I am posting about this on Twitter right now.",
]

CHANNELS = ["Email", "WhatsApp", "Phone", "Twitter/X", "Branch Walk-in", "Mobile App"]


def main():
    print("=" * 58)
    print("  MODULE 2 · Complaint Intelligence System")
    print("  2 Agents: Analyst → Strategist | Gemini 2.5 Flash")
    print("=" * 58)
    print("\nPaste a customer complaint (or press Enter for a sample):")
    print(SEP)

    complaint = input("Complaint: ").strip()
    if not complaint:
        complaint = SAMPLE_COMPLAINTS[0]
        print(f"\n[Using sample complaint]\n{complaint}\n")

    print("\nChannel options:", " | ".join(CHANNELS))
    channel = input("Channel (press Enter for Email): ").strip() or "Email"

    print(f"\n{SEP}")
    print("⚙️  Agent 1 (Analyst)    → classifying complaint...")
    print("⚙️  Agent 2 (Strategist) → building response strategy...")
    print(f"{SEP}\n")

    t0 = time.time()
    result = run(complaint, channel)
    elapsed = round(time.time() - t0, 1)

    print(f"{'─'*20} AGENT 1: COMPLAINT ANALYSIS {'─'*20}")
    print(result["analysis"])
    print(f"\n{'─'*20} AGENT 2: RESPONSE STRATEGY {'─'*21}")
    print(result["strategy"])
    print(f"\n⚡ {elapsed}s\n{SEP}\n")


if __name__ == "__main__":
    main()
