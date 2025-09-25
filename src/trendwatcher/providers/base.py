"""Base classes for trend data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import TrendSignal


class TrendProvider(ABC):
    """Abstract base class for all platform-specific providers."""

    name: str
    weight: float

    def __init__(self, name: str, *, weight: float = 1.0) -> None:
        self.name = name
        self.weight = weight

    @abstractmethod
    async def fetch_trends(self) -> Sequence[TrendSignal]:
        """Return a list of trending signals for the provider."""

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"{self.__class__.__name__}(name={self.name!r}, weight={self.weight})"
