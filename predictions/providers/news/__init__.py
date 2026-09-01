"""News headline feed Adapter (spec §19). MVP ships a Mock implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class NewsHeadline:
    title: str
    url: str
    source_name: str


class NewsDataProvider(ABC):
    @abstractmethod
    def get_headlines(self, query: str, limit: int = 5) -> list[NewsHeadline]: ...


class MockNewsDataProvider(NewsDataProvider):
    def get_headlines(self, query: str, limit: int = 5) -> list[NewsHeadline]:
        return [
            NewsHeadline(title=f"{query}に関する市場関係者の見方 ({i + 1})", url="#", source_name="Mock News Wire")
            for i in range(limit)
        ]
