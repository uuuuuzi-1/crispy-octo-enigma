"""Tests for the trend aggregation pipeline."""

from __future__ import annotations

import asyncio

from trendwatcher.aggregator import TrendAggregator
from trendwatcher.models import DemographicSlice, TrendSignal
from trendwatcher.providers.base import TrendProvider
from trendwatcher.providers.sample import SampleProvider


def _build_signal(term: str, platform: str, score: float, **metadata) -> TrendSignal:
    return TrendSignal(
        term=term,
        platform=platform,
        raw_score=score,
        category=metadata.get("category"),
        demographics=metadata.get("demographics", []),
        metadata=metadata.get("metadata", {}),
        rank=metadata.get("rank"),
    )


def test_aggregator_combines_signals() -> None:
    signals_music = [
        _build_signal(
            "Aurora Skies",
            "YouTube",
            95,
            category="music",
            demographics=[DemographicSlice(label="18-24", value=60)],
            metadata={"keywords": ["pop", "live"]},
        ),
        _build_signal(
            "Aurora Skies",
            "Spotify",
            82,
            category="music",
            demographics=[DemographicSlice(label="Global", value=40)],
            metadata={"artist": "DJ Nova"},
        ),
    ]
    sports_signal = _build_signal(
        "City Marathon",
        "X",
        70,
        category="sports",
        demographics=[DemographicSlice(label="25-34", value=50)],
        metadata={"keywords": ["running"]},
    )

    providers = [
        SampleProvider("YouTube", [signals_music[0]]),
        SampleProvider("Spotify", [signals_music[1]]),
        SampleProvider("X", [sports_signal]),
    ]

    aggregator = TrendAggregator(providers, smoothing=1.0)
    report = asyncio.run(aggregator.collect_once())
    assert len(report.trends) == 2

    music_trend = next(trend for trend in report.trends if trend.term == "Aurora Skies")
    assert music_trend.score == 88.5
    assert "music" in music_trend.categories
    assert music_trend.platform_breakdown["YouTube"]["score"] == 95
    assert music_trend.platform_breakdown["Spotify"]["score"] == 82

    sports_trend = next(trend for trend in report.trends if trend.term == "City Marathon")
    assert sports_trend.categories[0] == "sports"
    assert sports_trend.demographics[0].label == "25-34"


def test_provider_failure_is_reported() -> None:
    class FailingProvider(TrendProvider):
        def __init__(self) -> None:
            super().__init__("Failing", weight=1.0)

        async def fetch_trends(self):  # type: ignore[override]
            raise RuntimeError("boom")

    working_provider = SampleProvider(
        "YouTube",
        [
            _build_signal(
                "Test",
                "YouTube",
                90,
                category="music",
                demographics=[DemographicSlice(label="Global", value=100)],
            )
        ],
    )

    aggregator = TrendAggregator([FailingProvider(), working_provider], smoothing=1.0)
    report = asyncio.run(aggregator.collect_once())
    assert len(report.trends) == 1
    assert report.notes is not None
    assert "Failing" in report.notes
