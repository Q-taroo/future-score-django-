"""AI Prediction Service — provider interface (spec §17).

Every LLM vendor integration implements PredictionAIProvider. Keeping the
interface this narrow means swapping OpenAI <-> Anthropic <-> Google, or
adding a new one, never touches call sites — only get_ai_provider()'s
factory (in __init__.py) changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError


class AIPredictionOutput(BaseModel):
    """Structured-output contract every provider must satisfy. Even
    though a provider may call an LLM that returns free-form text, the
    adapter is responsible for coercing that into this shape and
    validating it here before it's trusted anywhere else in the app — we
    never persist or display a raw, unvalidated LLM response."""

    probability: float = Field(ge=0, le=1)  # P(YES)
    confidence: float = Field(ge=0, le=1)  # provider's self-reported confidence
    reasoning_summary: str = Field(min_length=1, max_length=2000)
    model: str


class AIProviderValidationError(Exception):
    def __init__(self, original: ValidationError):
        super().__init__(str(original))
        self.original = original


@dataclass(frozen=True)
class PredictionInputForAI:
    id: str
    title: str
    description: str
    category: str
    option_a: str
    option_b: str
    deadline: object  # datetime, kept loosely typed to avoid a django import here


class PredictionAIProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_prediction(self, prediction: PredictionInputForAI) -> AIPredictionOutput: ...

    def validate(self, raw: dict) -> AIPredictionOutput:
        try:
            return AIPredictionOutput.model_validate(raw)
        except ValidationError as exc:
            raise AIProviderValidationError(exc) from exc
