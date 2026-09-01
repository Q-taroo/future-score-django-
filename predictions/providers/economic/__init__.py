"""Economic indicator data Adapter (spec §19) — CPI, GDP, unemployment,
policy rates. MVP ships a Mock implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

MOCK_VALUES = {
    "CPI_JP": (2.8, "%YoY"),
    "GDP_JP": (1.1, "%QoQ annualized"),
    "UNEMPLOYMENT_JP": (2.4, "%"),
    "POLICY_RATE_JP": (0.5, "%"),
    "POLICY_RATE_US": (5.25, "%"),
}


@dataclass(frozen=True)
class EconomicIndicatorValue:
    indicator: str
    value: float
    unit: str


class EconomicDataProvider(ABC):
    @abstractmethod
    def get_indicator(self, indicator: str) -> EconomicIndicatorValue: ...


class MockEconomicDataProvider(EconomicDataProvider):
    def get_indicator(self, indicator: str) -> EconomicIndicatorValue:
        value, unit = MOCK_VALUES.get(indicator, (0, ""))
        return EconomicIndicatorValue(indicator=indicator, value=value, unit=unit)
