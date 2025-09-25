"""Core data models for the TrendWatcher toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence


@dataclass(frozen=True)
class DemographicSlice:
    """Represents an audience segment interested in a trend."""

    label: str
    value: float
    unit: str = "percentage"

    def as_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the slice."""

        return {"label": self.label, "value": self.value, "unit": self.unit}


@dataclass
class TrendSignal:
    """A single data point returned by a provider for a term."""

    term: str
    platform: str
    raw_score: float
    category: Optional[str] = None
    demographics: List[DemographicSlice] = field(default_factory=list)
    metadata: MutableMapping[str, Any] = field(default_factory=dict)
    rank: Optional[int] = None
    region: Optional[str] = None
    url: Optional[str] = None

    def normalized_score(self) -> float:
        """Return the raw score constrained to the range [0, 100]."""

        return max(0.0, min(100.0, float(self.raw_score)))

    def primary_genre(self) -> Optional[str]:
        """Read the genre directly from metadata if present."""

        genre = self.metadata.get("genre") if self.metadata else None
        return str(genre) if genre is not None else self.category

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the signal."""

        return {
            "term": self.term,
            "platform": self.platform,
            "score": self.normalized_score(),
            "category": self.category,
            "demographics": [d.as_dict() for d in self.demographics],
            "metadata": dict(self.metadata),
            "rank": self.rank,
            "region": self.region,
            "url": self.url,
        }


@dataclass
class AggregatedTrend:
    """A unified view of a trending term across multiple platforms."""

    term: str
    score: float
    categories: Sequence[str]
    demographics: Sequence[DemographicSlice]
    platform_breakdown: Mapping[str, Mapping[str, Any]]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    narrative: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return the trend in dict form suitable for serialisation."""

        return {
            "term": self.term,
            "score": self.score,
            "categories": list(self.categories),
            "demographics": [d.as_dict() for d in self.demographics],
            "platform_breakdown": {k: dict(v) for k, v in self.platform_breakdown.items()},
            "metadata": dict(self.metadata),
            "narrative": self.narrative,
        }


@dataclass
class TrendReport:
    """A snapshot of the current cross-platform trend landscape."""

    generated_at: datetime
    trends: Sequence[AggregatedTrend]
    providers_used: Sequence[str]
    notes: Optional[str] = None

    @classmethod
    def create(
        cls,
        trends: Sequence[AggregatedTrend],
        providers_used: Sequence[str],
        notes: Optional[str] = None,
    ) -> "TrendReport":
        """Factory for generating a report with the current timestamp."""

        return cls(datetime.now(tz=timezone.utc), trends, providers_used, notes)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the report."""

        return {
            "generated_at": self.generated_at.isoformat(),
            "providers": list(self.providers_used),
            "trends": [trend.to_dict() for trend in self.trends],
            "notes": self.notes,
        }
