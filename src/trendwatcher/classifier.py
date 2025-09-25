"""Utilities for categorising trend signals by genre."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable, Mapping, MutableMapping, Optional

from .models import TrendSignal


class GenreClassifier:
    """Simple keyword-driven genre classifier.

    The classifier uses a multi-level keyword map to infer a genre for a term
    when the provider does not supply one.  The heuristic is intentionally
    lightweight so that it can run cheaply for every update tick while still
    yielding meaningful categories for downstream analysis.
    """

    DEFAULT_KEYWORDS: Mapping[str, Iterable[str]] = {
        "music": (
            "album",
            "single",
            "track",
            "song",
            "ep",
            "mixtape",
            "tour",
            "concert",
            "dj",
            "spotify",
            "apple music",
            "billboard",
        ),
        "film & tv": (
            "movie",
            "film",
            "series",
            "episode",
            "season",
            "netflix",
            "hbo",
            "disney",
            "youtube",
        ),
        "sports": (
            "vs",
            "match",
            "game",
            "league",
            "tournament",
            "cup",
            "nba",
            "nfl",
            "soccer",
            "goal",
        ),
        "politics": (
            "election",
            "policy",
            "vote",
            "senate",
            "president",
            "minister",
            "campaign",
        ),
        "technology": (
            "ai",
            "iphone",
            "android",
            "update",
            "software",
            "release",
            "beta",
            "patch",
            "robot",
        ),
        "gaming": (
            "gameplay",
            "dlc",
            "playstation",
            "xbox",
            "switch",
            "pc",
            "twitch",
            "esports",
        ),
        "fashion": (
            "collection",
            "runway",
            "style",
            "outfit",
            "look",
            "brand",
        ),
        "finance": (
            "stock",
            "earnings",
            "crypto",
            "bitcoin",
            "market",
            "ipo",
            "merger",
        ),
    }

    def __init__(
        self,
        keyword_map: Optional[Mapping[str, Iterable[str]]] = None,
        *,
        default_genre: str = "general",
    ) -> None:
        self._keyword_map: MutableMapping[str, set[str]] = defaultdict(set)
        for genre, keywords in (keyword_map or self.DEFAULT_KEYWORDS).items():
            self._keyword_map[genre] = {kw.lower() for kw in keywords}
        self._default_genre = default_genre

    def classify(self, signal: TrendSignal) -> str:
        """Infer a genre for the provided signal."""

        # Prefer explicit metadata from the provider when available.
        explicit = signal.primary_genre()
        if explicit:
            return explicit

        haystack_components = list(
            filter(
                None,
                [
                    signal.term,
                    *(signal.metadata.get("keywords", []) if signal.metadata else []),
                    signal.metadata.get("description", "") if signal.metadata else "",
                ],
            )
        )
        haystack = " ".join(haystack_components).lower()
        tokens = set(re.findall(r"[a-z0-9']+", haystack))

        for genre, keywords in self._keyword_map.items():
            for keyword in keywords:
                if " " in keyword:
                    if keyword in haystack:
                        return genre
                elif keyword in tokens:
                    return genre

        return self._default_genre

    @property
    def default_genre(self) -> str:
        """Return the genre assigned when no rule matches."""

        return self._default_genre
