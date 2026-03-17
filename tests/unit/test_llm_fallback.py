"""Tests for LLM fallback math recognition."""

from unittest.mock import patch, MagicMock
from scimarkdown.llm.fallback import LLMFallback
from scimarkdown.config import SciMarkdownConfig


def test_llm_disabled():
    config = SciMarkdownConfig(llm_enabled=False)
    fallback = LLMFallback(config)
    result = fallback.recognize_math("x squared")
    assert result is None


def test_llm_not_available():
    config = SciMarkdownConfig(llm_enabled=True, llm_api_key_env="NONEXISTENT_KEY_12345")
    fallback = LLMFallback(config)
    result = fallback.recognize_math("some formula")
    assert result is None


@patch("scimarkdown.llm.fallback._call_openai")
def test_llm_openai_call(mock_call):
    mock_call.return_value = r"x^{2} + y^{2} = z^{2}"
    config = SciMarkdownConfig(llm_enabled=True, llm_provider="openai")
    fallback = LLMFallback(config)
    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = fallback.recognize_math("x squared plus y squared equals z squared")
    assert result is not None
    assert result.latex == r"x^{2} + y^{2} = z^{2}"
    assert result.source_type == "llm"


@patch("scimarkdown.llm.fallback._call_openai")
def test_llm_not_math(mock_call):
    mock_call.return_value = "NOT_MATH"
    config = SciMarkdownConfig(llm_enabled=True, llm_provider="openai")
    fallback = LLMFallback(config)
    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = fallback.recognize_math("just a regular sentence")
    assert result is None


@patch("scimarkdown.llm.fallback._call_openai")
def test_llm_api_failure(mock_call):
    mock_call.return_value = None
    config = SciMarkdownConfig(llm_enabled=True, llm_provider="openai")
    fallback = LLMFallback(config)
    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = fallback.recognize_math("some formula")
    assert result is None
