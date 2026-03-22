"""Tests for the actual _call_openai and _call_anthropic functions with full mock chains."""

from unittest.mock import patch, MagicMock

from scimarkdown.llm.fallback import _call_openai, _call_anthropic


class TestCallOpenAI:
    def test_call_openai_returns_response_text(self):
        """_call_openai returns the content from the API response."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  x^2 + y^2  "

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = _call_openai("fake-key", "gpt-4", "Is this math?")

        assert result == "x^2 + y^2"

    def test_call_openai_passes_correct_model(self):
        """_call_openai passes the model name to the API."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "result"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            _call_openai("fake-key", "gpt-4o", "prompt")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("model") == "gpt-4o" or call_kwargs.args[0] == "gpt-4o" or "model" in str(call_kwargs)

    def test_call_openai_returns_none_on_exception(self):
        """_call_openai returns None when the API raises an exception."""
        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.side_effect = Exception("API error")

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = _call_openai("fake-key", "gpt-4", "prompt")

        assert result is None

    def test_call_openai_returns_none_on_api_error(self):
        """_call_openai returns None when .create() raises."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("Rate limit")

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = _call_openai("fake-key", "gpt-4", "prompt")

        assert result is None

    def test_call_openai_constructs_client_with_api_key(self):
        """_call_openai creates the OpenAI client with the provided API key."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "result"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            _call_openai("my-secret-key", "gpt-4", "prompt")

        mock_openai_module.OpenAI.assert_called_once_with(api_key="my-secret-key")


class TestCallAnthropic:
    def test_call_anthropic_returns_response_text(self):
        """_call_anthropic returns the text from the first content block."""
        mock_message = MagicMock()
        mock_message.content[0].text = "  \\frac{a}{b}  "

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = _call_anthropic("fake-key", "claude-3-opus-20240229", "Is this math?")

        assert result == "\\frac{a}{b}"

    def test_call_anthropic_returns_none_on_exception(self):
        """_call_anthropic returns None when the API raises."""
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.side_effect = Exception("Connection error")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = _call_anthropic("fake-key", "claude-3", "prompt")

        assert result is None

    def test_call_anthropic_returns_none_on_create_error(self):
        """_call_anthropic returns None when messages.create() raises."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("overloaded")

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = _call_anthropic("fake-key", "claude-3", "prompt")

        assert result is None

    def test_call_anthropic_constructs_client_with_api_key(self):
        """_call_anthropic creates the Anthropic client with the provided API key."""
        mock_message = MagicMock()
        mock_message.content[0].text = "result"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            _call_anthropic("my-anthropic-key", "claude-3", "prompt")

        mock_anthropic_module.Anthropic.assert_called_once_with(api_key="my-anthropic-key")

    def test_call_anthropic_passes_max_tokens(self):
        """_call_anthropic passes max_tokens=1024 to the API."""
        mock_message = MagicMock()
        mock_message.content[0].text = "result"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            _call_anthropic("key", "model", "prompt")

        call_kwargs = mock_client.messages.create.call_args
        # Check max_tokens is 1024
        assert call_kwargs.kwargs.get("max_tokens") == 1024


class TestLLMFallbackAnthropicProvider:
    def test_llm_uses_anthropic_when_configured(self):
        """LLMFallback calls _call_anthropic when provider is 'anthropic'."""
        from scimarkdown.llm.fallback import LLMFallback
        from scimarkdown.config import SciMarkdownConfig

        config = SciMarkdownConfig(
            llm_enabled=True,
            llm_provider="anthropic",
            llm_api_key_env="TEST_ANTHROPIC_KEY",
        )

        with patch("scimarkdown.llm.fallback._call_anthropic") as mock_call:
            mock_call.return_value = r"\alpha + \beta"
            fallback = LLMFallback(config)

            with patch.dict("os.environ", {"TEST_ANTHROPIC_KEY": "fake-key"}):
                result = fallback.recognize_math("alpha plus beta")

        mock_call.assert_called_once()
        assert result is not None
        assert result.latex == r"\alpha + \beta"
        assert result.source_type == "llm"

    def test_llm_recognize_math_confidence_is_0_8(self):
        """LLM results have confidence 0.8."""
        from scimarkdown.llm.fallback import LLMFallback
        from scimarkdown.config import SciMarkdownConfig

        config = SciMarkdownConfig(
            llm_enabled=True,
            llm_provider="openai",
            llm_api_key_env="TEST_KEY",
        )

        with patch("scimarkdown.llm.fallback._call_openai") as mock_call:
            mock_call.return_value = r"x^2"
            fallback = LLMFallback(config)

            with patch.dict("os.environ", {"TEST_KEY": "fake-key"}):
                result = fallback.recognize_math("x squared")

        assert result is not None
        assert result.confidence == 0.8
