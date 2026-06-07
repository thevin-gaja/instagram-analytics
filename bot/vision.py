import re
import json
import base64
import anthropic

EXTRACTION_PROMPT = """Extract all visible Instagram Reel Insights metrics from this screenshot.
Return ONLY a single valid JSON object — no explanation, no markdown, no code fences.
Use null for any value you cannot find with confidence.

Required keys:
{
  "hours_since_post": number (from the graph tooltip label, e.g. "6h" → 6; null if not visible),
  "views_at_hour":    number (the pinned value shown on the views-over-time graph tooltip; null if not visible),
  "views":            number (total Views from the summary card),
  "reached":          number (Accounts reached),
  "watchTime":        number (Average watch time in seconds),
  "follows":          number,
  "likes":            number,
  "comments":         number,
  "reposts":          number,
  "shares":           number (sends),
  "saves":            number,
  "skipRate":         number (percentage, e.g. 51.0; null if not visible),
  "likeRate":         number (null if not visible),
  "shareRate":        number (null if not visible),
  "saveRate":         number (null if not visible),
  "repostRate":       number (null if not visible),
  "commentRate":      number (null if not visible),
  "ret3s":            number (retention % at 3s; null if not visible),
  "retEnd":           number (end-of-video retention %; null if not visible),
  "profileVisits":    number (null if not visible),
  "nonFollower":      number (% non-follower reach; null if not visible),
  "topSource":        string (e.g. "Reels tab (53.6%)"; null if not visible),
  "ageBracket":       string (e.g. "18-24 (55.7%)"; null if not visible)
}"""


def _media_type(image_bytes: bytes) -> str:
    return "image/jpeg" if image_bytes[:2] == b"\xff\xd8" else "image/png"


def extract_metrics(image_bytes: bytes, api_key: str) -> dict:
    """Extract Instagram analytics metrics from a screenshot using Claude Vision."""
    client = anthropic.Anthropic(api_key=api_key)
    image_data = base64.standard_b64encode(image_bytes).decode()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _media_type(image_bytes),
                        "data": image_data,
                    },
                },
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
