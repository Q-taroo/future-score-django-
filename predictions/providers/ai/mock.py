"""Deterministic-ish mock so seed data / screenshots / tests don't flap.
Uses a simple hash of the prediction id to derive a stable pseudo
probability plus category-flavored reasoning text — good enough to make
the UI feel alive without any API key or network call.
"""

from .base import AIPredictionOutput, PredictionAIProvider, PredictionInputForAI

REASONING_TEMPLATES = {
    "MONETARY_POLICY": "中央銀行の直近の声明、インフレ動向、雇用統計のトレンドを踏まえたシナリオ分析です。",
    "FOREX": "金利差、貿易収支、リスクセンチメントを踏まえたテクニカル・ファンダメンタルズ分析です。",
    "STOCK_MARKET": "企業業績見通し、金利環境、過去のボラティリティパターンを考慮しています。",
    "ECONOMIC_INDICATOR": "先行指標および市場コンセンサス予想との比較に基づく分析です。",
    "COMMODITY": "需給バランス、地政学リスク、季節性を考慮した分析です。",
    "MACROECONOMY": "複数のマクロ経済指標を統合したシナリオ分析です。",
}


def _hash_to_unit_interval(text: str) -> float:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return (h % 10000) / 10000


class MockAIProvider(PredictionAIProvider):
    provider_name = "MOCK"

    def generate_prediction(self, prediction: PredictionInputForAI) -> AIPredictionOutput:
        base = _hash_to_unit_interval(prediction.id + prediction.title)
        # Keep it away from the extremes (0/1) so it reads as a genuine
        # probabilistic forecast rather than a certainty claim.
        probability = min(0.92, max(0.08, base))
        confidence = 0.55 + _hash_to_unit_interval(prediction.id + "conf") * 0.35

        template = REASONING_TEMPLATES.get(prediction.category, "公開情報に基づく一般的なシナリオ分析です。")

        raw = {
            "probability": round(probability, 4),
            "confidence": round(confidence, 4),
            "reasoning_summary": (
                f"[MOCK AI分析] {template} 現時点の確率は{round(probability * 100)}%と推定しました。"
                "本予測は情報提供を目的とし、投資助言ではありません。"
            ),
            "model": "mock-analyst-v1",
        }
        # Never trust a provider blindly, even our own mock — validate
        # the exact same way a real LLM's JSON response would be.
        return self.validate(raw)
