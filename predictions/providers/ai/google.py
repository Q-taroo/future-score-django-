import json

import requests

from .base import AIPredictionOutput, PredictionAIProvider, PredictionInputForAI

SYSTEM_PROMPT = (
    "You are a financial/economic forecasting analyst. Estimate the probability (0-1) that the "
    'outcome will be "YES". Respond with ONLY this JSON shape, no other text: '
    '{"probability": number, "confidence": number, "reasoning_summary": string}. '
    "This is informational analysis, not investment advice."
)


class GoogleAIProvider(PredictionAIProvider):
    provider_name = "GOOGLE"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate_prediction(self, prediction: PredictionInputForAI) -> AIPredictionOutput:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        res = requests.post(
            url,
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    f"{SYSTEM_PROMPT}\n\nQuestion: {prediction.title}\nDetails: {prediction.description}\n"
                                    f"Options: {prediction.option_a} / {prediction.option_b}\nDeadline: {prediction.deadline}"
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=30,
        )
        res.raise_for_status()
        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = json.loads(text)
        raw["model"] = self.model
        return self.validate(raw)
