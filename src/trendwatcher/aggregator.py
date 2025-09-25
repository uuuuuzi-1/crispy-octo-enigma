"""Aggregation and analysis logic for cross-platform trends."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter, defaultdict
from typing import Any, AsyncIterator, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .classifier import GenreClassifier
from .models import AggregatedTrend, DemographicSlice, TrendReport, TrendSignal
from .providers.base import TrendProvider

LOGGER = logging.getLogger(__name__)


class TrendAggregator:
    """Collects signals from multiple providers and generates consolidated reports."""

    def __init__(
        self,
        providers: Sequence[TrendProvider],
        *,
        genre_classifier: Optional[GenreClassifier] = None,
        smoothing: float = 0.35,
    ) -> None:
        if not providers:
            raise ValueError("At least one provider must be supplied")
        self._providers = list(providers)
        self._genre_classifier = genre_classifier or GenreClassifier()
        self._smoothing = max(0.0, min(1.0, smoothing))
        self._previous_scores: Dict[str, float] = {}

    @property
    def providers(self) -> Sequence[TrendProvider]:
        """Return the configured providers."""

        return tuple(self._providers)

    async def collect_once(self) -> TrendReport:
        """Collect data from all providers and compute a fresh report."""

        tasks = [asyncio.create_task(self._collect_from_provider(provider)) for provider in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals: List[TrendSignal] = []
        providers_used: List[str] = []
        notes: List[str] = []
        for provider, result in zip(self._providers, results):
            if isinstance(result, Exception):
                message = f"Provider {provider.name} failed: {result}"
                LOGGER.exception(message)
                notes.append(message)
                continue
            providers_used.append(provider.name)
            signals.extend(result)

        aggregated_trends = self._aggregate(signals)
        note_text = "\n".join(notes) if notes else None
        return TrendReport.create(aggregated_trends, providers_used, note_text)

    def collect(self) -> TrendReport:
        """Synchronous helper that runs :meth:`collect_once` in a fresh event loop."""

        return asyncio.run(self.collect_once())

    async def stream(
        self,
        interval_seconds: float,
        *,
        stop_event: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[TrendReport]:
        """Continuously yield reports at the requested interval."""

        while True:
            report = await self.collect_once()
            yield report

            if stop_event and stop_event.is_set():
                break

            await asyncio.sleep(max(0.0, interval_seconds))

    async def _collect_from_provider(self, provider: TrendProvider) -> Sequence[TrendSignal]:
        """Fetch trends from an individual provider, applying the provider weight."""

        signals = await provider.fetch_trends()
        for signal in signals:
            if not signal.platform:
                signal.platform = provider.name
        return signals

    def _aggregate(self, signals: Iterable[TrendSignal]) -> Sequence[AggregatedTrend]:
        """Normalise and combine raw provider signals."""

        grouped: MutableMapping[str, Dict[str, Any]] = {}
        for signal in signals:
            key = signal.term.casefold().strip()
            if not key:
                continue

            provider_weight = 1.0
            for provider in self._providers:
                if provider.name == signal.platform:
                    provider_weight = provider.weight
                    break

            genre = self._genre_classifier.classify(signal)
            signal.category = genre
            score = signal.normalized_score()
            weighted_score = score * provider_weight

            bucket = grouped.setdefault(
                key,
                {
                    "term": signal.term,
                    "score_sum": 0.0,
                    "weight_sum": 0.0,
                    "categories": Counter(),
                    "demographics": defaultdict(float),
                    "platform_breakdown": {},
                    "regions": set(),
                    "urls": set(),
                    "metadata": defaultdict(set),
                },
            )

            bucket["score_sum"] += weighted_score
            bucket["weight_sum"] += provider_weight
            bucket["categories"][genre] += provider_weight
            for slice_ in signal.demographics:
                bucket["demographics"][slice_.label] += slice_.value * provider_weight
            bucket["platform_breakdown"][signal.platform] = {
                "score": score,
                "rank": signal.rank,
                "weight": provider_weight,
                "region": signal.region,
            }
            if signal.region:
                bucket["regions"].add(signal.region)
            if signal.url:
                bucket["urls"].add(signal.url)
            for meta_key, meta_value in signal.metadata.items():
                bucket["metadata"][meta_key].add(str(meta_value))

        aggregated: List[AggregatedTrend] = []
        for key, bucket in grouped.items():
            weight_sum = bucket["weight_sum"] or 1.0
            score = bucket["score_sum"] / weight_sum

            previous = self._previous_scores.get(key)
            if previous is not None:
                score = self._smoothing * score + (1 - self._smoothing) * previous
            self._previous_scores[key] = score

            categories = [genre for genre, _ in bucket["categories"].most_common(3) if genre]
            demographic_total = sum(bucket["demographics"].values())
            demographics: List[DemographicSlice] = []
            if demographic_total:
                for label, value in sorted(bucket["demographics"].items(), key=lambda item: item[1], reverse=True):
                    percent = (value / demographic_total) * 100
                    demographics.append(DemographicSlice(label=label, value=round(percent, 2)))

            metadata: Dict[str, Any] = {
                "regions": sorted(bucket["regions"]),
                "urls": sorted(bucket["urls"]),
            }
            for meta_key, values in bucket["metadata"].items():
                metadata[meta_key] = sorted(values)

            breakdown = bucket["platform_breakdown"]
            narrative = self._build_narrative(bucket["term"], categories, demographics, breakdown)

            aggregated.append(
                AggregatedTrend(
                    term=bucket["term"],
                    score=round(score, 2),
                    categories=categories or [self._genre_classifier.default_genre],
                    demographics=demographics,
                    platform_breakdown=breakdown,
                    metadata=metadata,
                    narrative=narrative,
                )
            )

        aggregated.sort(key=lambda trend: trend.score, reverse=True)
        return aggregated

    @staticmethod
    def _build_narrative(
        term: str,
        categories: Sequence[str],
        demographics: Sequence[DemographicSlice],
        breakdown: Mapping[str, Mapping[str, Any]],
    ) -> str:
        """Generate a human-readable description for a trend."""

        primary_category = categories[0] if categories else "general interest"
        if demographics:
            demo_summary = ", ".join(f"{slice_.label} ({slice_.value:.1f}%)" for slice_ in demographics[:3])
        else:
            demo_summary = "no demographic segments available"

        top_platforms = sorted(
            ((platform, data.get("score", 0.0)) for platform, data in breakdown.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        platform_summary = ", ".join(f"{name} ({score:.1f})" for name, score in top_platforms[:3])

        return (
            f"{term} is trending in {primary_category} with strongest engagement from {demo_summary}. "
            f"Key platforms: {platform_summary or 'no data'}"
        )
