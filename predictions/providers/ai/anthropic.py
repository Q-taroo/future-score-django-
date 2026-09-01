import json
import re

import requests

from .base import AIPredictionOutput, PredictionAIProvider, PredictionInputForAI

SYSTEM_PROMPT = (
    "あなたは金融・経済分野の予測アナリストです。与えられた質問について、YESになる確率を0から1の間で"
    "推定してください。必ず以下のJSON形式のみで出力してください。他のテキストは一切含めないでください。\n"
    '{"probability": number, "confidence": number, "reasoning_summary": string}\n'
    "これは投資助言ではなく、情報分析であることを踏まえた客観的な分析にしてください。"
)


def _extract_json(text: str) -> str:
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else text


class AnthropicAIProvider(PredictionAIProvider):
    provider_name = "ANTHROPIC"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest"):
        self.api_key = api_key
        self.model = model

    def generate_prediction(self, prediction: PredictionInputForAI) -> AIPredictionOutput:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": 512,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"質問: {prediction.title}\n詳細: {prediction.description}\n"
                            f"選択肢: {prediction.option_a} / {prediction.option_b}\n締切: {prediction.deadline}"
                        ),
                    }
                ],
            },
            timeout=30,
        )
        res.raise_for_status()
        content = res.json()["content"]
        text = next((c["text"] for c in content if c.get("type") == "text"), "{}")
        raw = json.loads(_extract_json(text))
        raw["model"] = self.model
        return self.validate(raw)
