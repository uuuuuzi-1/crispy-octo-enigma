"""Sample providers and utilities for testing and prototyping."""

from __future__ import annotations

import asyncio
import copy
from typing import Iterable, Sequence

from ..models import TrendSignal
from .base import TrendProvider


class SampleProvider(TrendProvider):
    """A lightweight provider that returns a pre-defined list of signals."""

    def __init__(self, name: str, signals: Iterable[TrendSignal], *, weight: float = 1.0) -> None:
        super().__init__(name, weight=weight)
        self._signals = [copy.deepcopy(signal) for signal in signals]

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        await asyncio.sleep(0)  # allow scheduling in async contexts
        return [copy.deepcopy(signal) for signal in self._signals]
