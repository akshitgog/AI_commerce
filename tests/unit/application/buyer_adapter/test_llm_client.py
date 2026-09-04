"""Deterministic tests for the litellm-backed LLM client.

Uses unittest.mock to patch ``litellm.completion`` so no real HTTP calls are
made. Verifies tool-call parsing, error handling, and missing API key
fallback. Tool-schema wiring is covered by the orchestrator tests.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_commerce_gateway.application.buyer_adapter.llm_client import (
    OpenAILLMClient,
)

_TEST_ENV = {
    "LLM_API_KEY": "test-key-123",
    "LLM_BASE_URL": "http://localhost:9999/v1",
    "LLM_MODEL": "gpt-4o-mini",
}


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the lru_cache on get_settings so env changes take effect."""
    from ai_commerce_gateway.core.config import get_settings

    get_settings.cache_clear()


def _mock_litellm_response(
    content: str | None = None,
    tool_calls: list[MagicMock] | None = None,
) -> MagicMock:
    """Build a mock litellm completion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    response = MagicMock()
    response.choices = [MagicMock(message=message)]
    return response


def _mock_tool_call(name: str, arguments: dict[str, object]) -> MagicMock:
    tool_call = MagicMock()
    tool_call.function.name = name
    tool_call.function.arguments = json.dumps(arguments)
    return tool_call


class TestOpenAILLMClientMissingKey:
    """When LLM_API_KEY is not set, the client should fall back gracefully."""

    @patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=False)
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

    @patch.dict("os.environ", _TEST_ENV, clear=False)
    @patch("litellm.completion")
    def test_tool_call_parsing(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value = _mock_litellm_response(
            tool_calls=[
                _mock_tool_call("search_catalog", {"merchant_id": "mer_123"}),
            ]
        )
        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "find phones"}],
            tools=[
                {
                    "name": "search_catalog",
                    "description": "Search",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ],
        )
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search_catalog"
        assert result.tool_calls[0].arguments == {"merchant_id": "mer_123"}
        # The system prompt hard boundary must be part of the request.
        sent_messages = mock_completion.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "CANNOT approve" in sent_messages[0]["content"]

    @patch.dict("os.environ", _TEST_ENV, clear=False)
    @patch("litellm.completion")
    def test_text_only_response(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value = _mock_litellm_response(content="Hello!")
        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "hi"}],
            tools=[],
        )
        assert result.text == "Hello!"
        assert result.tool_calls is None


class TestOpenAILLMClientErrors:
    """Provider errors should be caught and mapped gracefully."""

    @patch.dict("os.environ", _TEST_ENV, clear=False)
    @patch("litellm.completion")
    def test_http_error_returns_graceful_message(self, mock_completion: MagicMock) -> None:
        mock_completion.side_effect = Exception("503 Service Unavailable")
        client = OpenAILLMClient()
        result = client.generate(
            [{"role": "user", "content": "test"}],
            tools=[],
        )
        assert result.text is not None
        assert "trouble" in result.text.lower() or "sorry" in result.text.lower()
        assert result.tool_calls is None
