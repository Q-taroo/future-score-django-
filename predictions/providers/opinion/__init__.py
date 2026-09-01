"""Opinion/market-signal Adapter interface (spec §11/§19). MVP ships a
Mock implementation; a real one (news sentiment, search trends, social
listening, prediction-market odds, public statistics) plugs in behind the
same interface later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class OpinionSignalResult:
    source: str
    yes_probability: float
    no_probability: float
    sample_size: int


@dataclass(frozen=True)
class OpinionSignalInput:
    id: str
    title: str
    category: str


class OpinionDataProvider(ABC):
    source_name: str

    @abstractmethod
    def fetch_signal(self, input: OpinionSignalInput) -> OpinionSignalResult: ...


def _hash_to_unit_interval(text: str) -> float:
    h = 0
    for ch in text:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (h % 10000) / 10000


class MockOpinionProvider(OpinionDataProvider):
    source_name = "MOCK_SURVEY"

    def fetch_signal(self, input: OpinionSignalInput) -> OpinionSignalResult:
        yes = 0.15 + _hash_to_unit_interval(input.id + "opinion") * 0.7
        return OpinionSignalResult(
            source=self.source_name,
            yes_probability=round(yes, 4),
            no_probability=round(1 - yes, 4),
            sample_size=200 + int(_hash_to_unit_interval(input.id + "n") * 5000),
        )
