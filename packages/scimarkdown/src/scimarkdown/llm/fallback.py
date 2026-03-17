"""LLM fallback client for math recognition."""

import logging
import os
from typing import Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models.math_region import MathRegion

logger = logging.getLogger(__name__)

_MATH_PROMPT = """Analyze the following text and determine if it contains a mathematical formula or scientific expression. If it does, convert it to LaTeX notation. Return ONLY the LaTeX expression, nothing else. If it is not a formula, return "NOT_MATH".

Text: {text}"""


def _call_openai(api_key: str, model: str, prompt: str) -> Optional[str]:
    """Call OpenAI API and return the response text, or None on failure."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("OpenAI API call failed: %s", exc)
        return None


def _call_anthropic(api_key: str, model: str, prompt: str) -> Optional[str]:
    """Call Anthropic API and return the response text, or None on failure."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.warning("Anthropic API call failed: %s", exc)
        return None


class LLMFallback:
    """Fallback math recognizer that uses an LLM to convert text to LaTeX."""

    def __init__(self, config: SciMarkdownConfig) -> None:
        self._config = config

    def recognize_math(self, text: str) -> Optional[MathRegion]:
        """Try to recognize math in text using the configured LLM.

        Returns a MathRegion with source_type="llm" and confidence=0.8,
        or None if LLM is disabled, unavailable, or the text is not math.
        """
        if not self._config.llm_enabled:
            return None

        api_key = os.environ.get(self._config.llm_api_key_env)
        if not api_key:
            logger.warning(
                "LLM API key not found in environment variable '%s'",
                self._config.llm_api_key_env,
            )
            return None

        prompt = _MATH_PROMPT.format(text=text)
        provider = self._config.llm_provider.lower()

        if provider == "anthropic":
            result = _call_anthropic(api_key, self._config.llm_model, prompt)
        else:
            result = _call_openai(api_key, self._config.llm_model, prompt)

        if result is None or result.strip() == "NOT_MATH":
            return None

        return MathRegion(
            position=0,
            original_text=text,
            latex=result,
            source_type="llm",
            confidence=0.8,
        )
