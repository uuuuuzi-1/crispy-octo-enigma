"""Apple Music charts provider."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from urllib import parse, request

from ..models import DemographicSlice, TrendSignal
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


class AppleMusicTrendsProvider(TrendProvider):
    """Fetch the Apple Music charts via the MusicKit API."""

    API_URL = "https://api.music.apple.com/v1/catalog/{storefront}/charts"

    def __init__(
        self,
        developer_token: Optional[str],
        *,
        storefront: str = "us",
        chart_types: Sequence[str] = ("songs", "albums"),
        limit: int = 20,
        weight: float = 1.0,
    ) -> None:
        super().__init__("Apple Music", weight=weight)
        self._token = developer_token
        self._storefront = storefront
        self._chart_types = chart_types
        self._limit = limit

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        if not self._token:
            raise RuntimeError("Apple Music developer token is required")

        params = {
            "types": ",".join(self._chart_types),
            "limit": self._limit,
            "chart": "most-played",
        }
        url = self.API_URL.format(storefront=self._storefront) + "?" + parse.urlencode(params)
        headers = {"Authorization": f"Bearer {self._token}"}
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._fetch_json, url, headers)
        results: Dict[str, Any] = data.get("results", {})
        signals: List[TrendSignal] = []
        for chart_type, entries in results.items():
            for index, entry in enumerate(entries.get("data", []), start=1):
                attributes: Dict[str, Any] = entry.get("attributes", {})
                name = attributes.get("name") or entry.get("id")
                artists = attributes.get("artistName")
                genres = attributes.get("genreNames", [])
                score = (self._limit - index + 1) / self._limit * 100
                metadata = {
                    "chart_type": chart_type,
                    "artist": artists,
                    "genres": genres,
                    "release_date": attributes.get("releaseDate"),
                }
                demographics = [DemographicSlice(label=self._storefront, value=100.0)]
                signals.append(
                    TrendSignal(
                        term=name or "Unknown",
                        platform=self.name,
                        raw_score=score,
                        category="music",
                        demographics=demographics,
                        metadata=metadata,
                        url=attributes.get("url"),
                        region=self._storefront.upper(),
                    )
                )
        return signals

    @staticmethod
    def _fetch_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        LOGGER.debug("Requesting Apple Music charts: %s", url)
        req = request.Request(url, headers=headers)  # type: ignore[arg-type]
        with request.urlopen(req, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        return json.loads(payload)
