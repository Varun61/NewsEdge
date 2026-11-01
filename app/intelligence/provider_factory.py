"""Factory for AI classification providers."""

from __future__ import annotations

import logging

from app.config import AIProvider, get_settings
from app.intelligence.ai_provider import BaseAIProvider
from app.intelligence.ollama_provider import OllamaProvider
from app.intelligence.openai_provider import OpenAIProvider

logger = logging.getLogger("newsedge.intelligence.factory")


def get_ai_provider() -> BaseAIProvider:
    """Return configured AI provider backend with fallback."""
    settings = get_settings()

    if settings.ai_provider == AIProvider.OPENAI:
        provider = OpenAIProvider(settings)
        if provider.is_available():
            logger.info("Using OpenAI AI provider (%s)", settings.openai_model)
            return provider
        logger.warning("OpenAI provider not available, falling back to Ollama or heuristic")

    provider = OllamaProvider(settings)
    if provider.is_available():
        logger.info("Using Ollama AI provider (%s)", settings.ollama_model)
    else:
        logger.warning("Ollama service not detected at %s. Will use rule-based fallback.", settings.ollama_base_url)

    return provider
