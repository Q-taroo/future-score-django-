"""Factory: reads settings.AI_PROVIDER and returns the matching
implementation. Defaults to MOCK so `manage.py runserver` works with zero
API keys configured. Falls back to MOCK (with a log warning, never a
crash) if a real provider is selected but its key is missing.
"""

import logging

from django.conf import settings

from .base import AIPredictionOutput, PredictionAIProvider, PredictionInputForAI  # noqa: F401
from .mock import MockAIProvider

logger = logging.getLogger(__name__)


def get_ai_provider() -> PredictionAIProvider:
    provider_name = (settings.AI_PROVIDER or "MOCK").upper()

    if provider_name == "OPENAI":
        if not settings.OPENAI_API_KEY:
            logger.warning("AI_PROVIDER=OPENAI but OPENAI_API_KEY is unset; falling back to MOCK")
            return MockAIProvider()
        from .openai import OpenAIProvider

        return OpenAIProvider(settings.OPENAI_API_KEY)

    if provider_name == "ANTHROPIC":
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("AI_PROVIDER=ANTHROPIC but ANTHROPIC_API_KEY is unset; falling back to MOCK")
            return MockAIProvider()
        from .anthropic import AnthropicAIProvider

        return AnthropicAIProvider(settings.ANTHROPIC_API_KEY)

    if provider_name == "GOOGLE":
        if not settings.GOOGLE_AI_API_KEY:
            logger.warning("AI_PROVIDER=GOOGLE but GOOGLE_AI_API_KEY is unset; falling back to MOCK")
            return MockAIProvider()
        from .google import GoogleAIProvider

        return GoogleAIProvider(settings.GOOGLE_AI_API_KEY)

    return MockAIProvider()
