import json
import pytest
from unittest.mock import MagicMock, patch
from bot.vision import extract_metrics

MOCK_RESPONSE_JSON = json.dumps({
    "hours_since_post": 6,
    "views_at_hour": 2324,
    "views": 2635,
    "reached": 1347,
    "watchTime": 19,
    "follows": 3,
    "likes": 142,
    "comments": 12,
    "reposts": 5,
    "shares": 13,
    "saves": 5,
    "skipRate": None,
    "likeRate": None,
    "shareRate": None,
    "saveRate": None,
    "repostRate": None,
    "commentRate": None,
    "ret3s": None,
    "retEnd": None,
    "profileVisits": None,
    "nonFollower": None,
    "topSource": None,
    "ageBracket": None
})


def _make_mock_client(response_text: str):
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def test_extract_metrics_returns_dict():
    mock_client = _make_mock_client(MOCK_RESPONSE_JSON)
    with patch("bot.vision.anthropic.Anthropic", return_value=mock_client):
        result = extract_metrics(b"fake_image_bytes", "fake_key")
    assert isinstance(result, dict)


def test_extract_metrics_parses_hours_since_post():
    mock_client = _make_mock_client(MOCK_RESPONSE_JSON)
    with patch("bot.vision.anthropic.Anthropic", return_value=mock_client):
        result = extract_metrics(b"fake_image_bytes", "fake_key")
    assert result["hours_since_post"] == 6


def test_extract_metrics_parses_views():
    mock_client = _make_mock_client(MOCK_RESPONSE_JSON)
    with patch("bot.vision.anthropic.Anthropic", return_value=mock_client):
        result = extract_metrics(b"fake_image_bytes", "fake_key")
    assert result["views"] == 2635


def test_extract_metrics_handles_json_in_markdown_fence():
    fenced = f"```json\n{MOCK_RESPONSE_JSON}\n```"
    mock_client = _make_mock_client(fenced)
    with patch("bot.vision.anthropic.Anthropic", return_value=mock_client):
        result = extract_metrics(b"fake_image_bytes", "fake_key")
    assert result["views"] == 2635


def test_extract_metrics_passes_image_as_base64():
    mock_client = _make_mock_client(MOCK_RESPONSE_JSON)
    with patch("bot.vision.anthropic.Anthropic", return_value=mock_client):
        extract_metrics(b"fake_image_bytes", "fake_key")
    call_args = mock_client.messages.create.call_args
    content = call_args.kwargs["messages"][0]["content"]
    image_block = next(b for b in content if b.get("type") == "image")
    assert image_block["source"]["type"] == "base64"
