"""
Module 1 — Basic CrewAI
main.py — standalone CLI chat. Run this independently of the UI.

Usage:
    cd module_1_basic_crewai
    python app/main.py

Commands during chat:
    clear  → reset session history
    exit   → quit
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.crew import run

SEP = "─" * 54


def main():
    print("=" * 54)
    print("  MODULE 1 · Basic CrewAI · Gemini 2.5 Flash")
    print("  1 Agent · Session Chat · type 'exit' to quit")
    print("=" * 54 + "\n")

    history = []          # session-only: cleared when process exits

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋  Bye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("👋  Bye!")
            break
        if user_input.lower() == "clear":
            history.clear()
            print("🗑  Session cleared.\n")
            continue

        print(f"\n{SEP}\n🤖  Agent thinking...\n")

        t0 = time.time()
        try:
            response = run(user_input, history=history)
            elapsed  = round(time.time() - t0, 1)

            # Store turn in session history
            history.append({"role": "user",      "content": user_input})
            history.append({"role": "assistant",  "content": response})

            print(response)
            print(f"\n⚡  {elapsed}s  |  turn {len(history)//2}\n{SEP}\n")

        except Exception as e:
            print(f"❌  Error: {e}\n")


if __name__ == "__main__":
    main()
