"""Deterministic tests for OpenAILLMClient (C3 I-1 fix).

Uses unittest.mock to patch httpx.Client so no real HTTP calls are made.
Verifies tool-call parsing, error handling, and missing API key fallback.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_commerce_gateway.application.buyer_adapter.llm_client import (
    OpenAILLMClient,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the lru_cache on get_settings so env changes take effect."""
    from ai_commerce_gateway.core.config import get_settings

    get_settings.cache_clear()


def _mock_openai_response(
    content: str | None = None,
    tool_calls: list[dict] | None = None,  # type: ignore[type-arg]
) -> MagicMock:
    """Build a mock httpx Response matching OpenAI's chat completion shape."""
    message: dict = {}  # type: ignore[type-arg]
    if content is not None:
        message["content"] = content
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    else:
        message["tool_calls"] = None

    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": message}],
    }
    return resp


class TestOpenAILLMClientMissingKey:
    """When LLM_API_KEY is not set, the client should fall back gracefully."""

    @patch.dict(
        "os.environ",
        {"LLM_API_KEY": "", "LLM_PROVIDER_URL": "http://x"},
        clear=False,
    )
    def test_missing_key_returns_simulation_message(self) -> None:
        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "hello"}],
            tools=[],
        )
        assert result.text is not None
        assert "configure" in result.text.lower() or "simulation" in result.text.lower()
        assert result.tool_calls is None


class TestOpenAILLMClientToolParsing:
    """When the LLM returns tool_calls, they should be parsed correctly."""

    @patch.dict(
        "os.environ",
        {
            "LLM_API_KEY": "test-key-123",
            "LLM_PROVIDER_URL": "http://localhost:9999/v1/chat/completions",
            "LLM_MODEL": "gpt-4o-mini",
        },
        clear=False,
    )
    @patch("ai_commerce_gateway.application.buyer_adapter.llm_client.httpx.Client")
    def test_tool_call_parsing(self, mock_client_cls: MagicMock) -> None:
        mock_resp = _mock_openai_response(
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search_catalog",
                        "arguments": json.dumps({"merchant_id": "mer_123"}),
                    },
                }
            ]
        )
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_resp
        mock_client_cls.return_value = mock_http

        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "find phones"}],
            tools=[
                {"name": "search_catalog", "description": "Search"},
            ],
        )
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search_catalog"
        assert result.tool_calls[0].arguments == {
            "merchant_id": "mer_123",
        }

    @patch.dict(
        "os.environ",
        {
            "LLM_API_KEY": "test-key-123",
            "LLM_PROVIDER_URL": "http://localhost:9999/v1/chat/completions",
        },
        clear=False,
    )
    @patch("ai_commerce_gateway.application.buyer_adapter.llm_client.httpx.Client")
    def test_text_only_response(self, mock_client_cls: MagicMock) -> None:
        mock_resp = _mock_openai_response(content="Hello!")
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = mock_resp
        mock_client_cls.return_value = mock_http

        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "hi"}],
            tools=[],
        )
        assert result.text == "Hello!"
        assert result.tool_calls is None


class TestOpenAILLMClientErrors:
    """HTTP errors should be caught and mapped gracefully."""

    @patch.dict(
        "os.environ",
        {
            "LLM_API_KEY": "test-key-123",
            "LLM_PROVIDER_URL": "http://localhost:9999/v1/chat/completions",
        },
        clear=False,
    )
    @patch("ai_commerce_gateway.application.buyer_adapter.llm_client.httpx.Client")
    def test_http_error_returns_graceful_message(self, mock_client_cls: MagicMock) -> None:
        import httpx

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = httpx.HTTPError("503 Service Unavailable")
        mock_client_cls.return_value = mock_http

        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "test"}],
            tools=[],
        )
        assert result.text is not None
        assert "trouble" in result.text.lower() or "sorry" in result.text.lower()
        assert result.tool_calls is None
