"""TrendWatcher: Cross-platform trend analysis toolkit."""

from .aggregator import TrendAggregator
from .models import AggregatedTrend, DemographicSlice, TrendReport, TrendSignal

__all__ = [
    "TrendAggregator",
    "AggregatedTrend",
    "DemographicSlice",
    "TrendReport",
    "TrendSignal",
]
