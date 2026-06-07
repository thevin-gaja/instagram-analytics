import json
import anthropic

QA_SYSTEM_PROMPT = """You are an analytics assistant for Instagram Reels performance data.
Answer questions concisely using numbers, percentages, and video IDs (e.g. D3, D7).
If data is missing or null, say so. Answer only from the data provided."""


def answer_question(question: str, cache: dict, api_key: str) -> str:
    """Answer a natural language question about the metrics cache using Claude."""
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=512,
        system=QA_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Data:\n{json.dumps(cache)}\n\nQuestion: {question}",
        }],
    )
    return response.content[0].text.strip()
