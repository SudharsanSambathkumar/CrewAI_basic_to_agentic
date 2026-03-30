"""
Module 1 — Basic CrewAI
tasks.py — Natural conversation task. No fixed format. Topic-guarded.
"""

from crewai import Task

# Topics the agent should handle
_ON_TOPIC = (
    "ai", "machine learning", "deep learning", "llm", "model", "neural",
    "data", "algorithm", "vector", "embedding", "rag", "agent", "crewai",
    "python", "code", "software", "api", "cloud", "docker", "database",
    "transformer", "attention", "gpt", "gemini", "claude", "prompt",
    "fine-tun", "train", "inference", "token", "context", "memory",
    "tech", "computer", "program", "deploy", "framework", "library",
    "what is", "how does", "explain", "difference", "why", "when", "how",
    "hi", "hello", "hey", "thanks", "thank", "good", "great", "ok",
    "yes", "no", "sure", "cool", "nice", "got it", "understand",
)

# Clear off-topic signals
_OFF_TOPIC = (
    "democracy", "politics", "election", "government", "recipe", "food",
    "cook", "sport", "football", "cricket", "movie", "film", "song",
    "music", "religion", "god", "prayer", "stock market", "invest",
    "love", "relationship", "dating", "weather", "news", "history",
)


def _check_topic(text: str) -> str:
    """Returns 'on', 'off', or 'unclear'."""
    lowered = text.lower()
    if any(t in lowered for t in _OFF_TOPIC):
        return "off"
    if any(t in lowered for t in _ON_TOPIC):
        return "on"
    return "unclear"


def create_explanation_task(user_input: str, agent, history: list = None) -> Task:
    # Build history block
    history_block = ""
    if history:
        lines = []
        for t in history[-6:]:
            label = "User" if t["role"] == "user" else "You"
            lines.append(f"{label}: {t['content']}")
        history_block = (
            "--- CONVERSATION SO FAR ---\n"
            + "\n".join(lines)
            + "\n--- END ---\n\n"
        )

    topic_status = _check_topic(user_input)

    if topic_status == "off":
        task_body = (
            "The user has asked about something outside your scope.\n"
            "Respond with ONE friendly sentence acknowledging their message "
            "and redirecting to AI/tech topics.\n"
            "Example: 'That's a bit outside my lane — I focus on AI and tech. "
            "Anything on that front I can help with?'\n"
            "Do not answer the off-topic question at all."
        )
        expected = "One polite redirect sentence."

    elif topic_status == "on":
        task_body = (
            "Reply naturally like a knowledgeable friend.\n\n"
            "Rules:\n"
            "- Match your response length to the complexity of the question\n"
            "- Simple question → 2-4 sentences is enough\n"
            "- Complex question → a few short paragraphs, no more\n"
            "- Use plain language, real examples where helpful\n"
            "- NO numbered sections, NO bold headers unless user asks\n"
            "- If you are not certain about something, say so honestly\n"
            "- Never make up facts, tools, or papers\n"
            "- Build on the conversation history — don't repeat yourself"
        )
        expected = "A natural, conversational reply. Length matches question complexity."

    else:
        # Greetings, unclear, very short messages
        task_body = (
            "Reply warmly and naturally in 1-2 sentences.\n"
            "If it's a greeting, say hi and invite them to ask about AI or tech.\n"
            "If it's vague, ask a clarifying question.\n"
            "Do NOT use any structured format."
        )
        expected = "A short, warm, natural reply of 1-2 sentences."

    return Task(
        description=(
            f"{history_block}"
            f"User message: {user_input}\n\n"
            f"{task_body}"
        ),
        expected_output=expected,
        agent=agent,
    )