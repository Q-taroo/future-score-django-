"""Unit tests for the Mock AI provider — no Django DB access needed,
just settings for pydantic-independent import. Verifies determinism
(same input -> same output, so seed data/screenshots/tests don't flap)
and that output always satisfies the validated AIPredictionOutput
contract."""

from predictions.providers.ai.base import AIPredictionOutput
from predictions.providers.ai.mock import MockAIProvider
from predictions.providers.ai.base import PredictionInputForAI


def _input(id="1", title="日銀は利上げするか？", category="MONETARY_POLICY"):
    return PredictionInputForAI(
        id=id, title=title, description="desc", category=category, option_a="YES", option_b="NO", deadline=None
    )


class TestMockAIProvider:
    def test_returns_validated_output(self):
        provider = MockAIProvider()
        output = provider.generate_prediction(_input())
        assert isinstance(output, AIPredictionOutput)
        assert 0 <= output.probability <= 1
        assert 0 <= output.confidence <= 1
        assert output.reasoning_summary

    def test_deterministic_for_same_input(self):
        provider = MockAIProvider()
        a = provider.generate_prediction(_input(id="42"))
        b = provider.generate_prediction(_input(id="42"))
        assert a.probability == b.probability
        assert a.reasoning_summary == b.reasoning_summary

    def test_different_ids_can_yield_different_probabilities(self):
        provider = MockAIProvider()
        a = provider.generate_prediction(_input(id="1"))
        b = provider.generate_prediction(_input(id="2"))
        # Not a strict guarantee for every possible pair, but true for
        # this provider's hash function across these two ids — guards
        # against a regression that makes the provider return a constant.
        assert (a.probability, a.reasoning_summary) != (b.probability, b.reasoning_summary)

    def test_probability_stays_away_from_certainty_extremes(self):
        provider = MockAIProvider()
        for i in range(20):
            output = provider.generate_prediction(_input(id=str(i)))
            assert 0.05 <= output.probability <= 0.95

    def test_never_offers_investment_advice_language(self):
        provider = MockAIProvider()
        output = provider.generate_prediction(_input())
        assert "投資助言ではありません" in output.reasoning_summary
