import json

import requests

from .base import AIPredictionOutput, PredictionAIProvider, PredictionInputForAI

SYSTEM_PROMPT = (
    "You are a financial/economic forecasting analyst. Estimate the probability (0-1) that the "
    'outcome will be "YES". Respond with ONLY this JSON shape, no other text: '
    '{"probability": number, "confidence": number, "reasoning_summary": string}. '
    "This is informational analysis, not investment advice."
)


class OpenAIProvider(PredictionAIProvider):
    provider_name = "OPENAI"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate_prediction(self, prediction: PredictionInputForAI) -> AIPredictionOutput:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"content-type": "application/json", "authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {prediction.title}\nDetails: {prediction.description}\n"
                            f"Options: {prediction.option_a} / {prediction.option_b}\nDeadline: {prediction.deadline}"
                        ),
                    },
                ],
            },
            timeout=30,
        )
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"]
        raw = json.loads(text)
        raw["model"] = self.model
        return self.validate(raw)
