import anthropic
from bot.analytics import build_analytics_summary

QA_SYSTEM_PROMPT = """You are an analytics assistant for Instagram Reels performance data.
You are given a pre-computed analytics summary. Answer questions using specific numbers,
video names, and percentages. Be concise. If data is missing (shown as —), say so.
Reference videos by name (e.g. "Day 10") or ID (e.g. V10), not just ID."""


def answer_question(question: str, cache: dict, api_key: str) -> str:
    """Answer a natural language question using a pre-computed analytics summary."""
    summary = build_analytics_summary(cache)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=QA_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"{summary}\n\nQuestion: {question}",
        }],
    )
    return response.content[0].text.strip()
