"""Provider for trending topics on X (formerly Twitter)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib import parse, request

from ..models import DemographicSlice, TrendSignal
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


class XTrendsProvider(TrendProvider):
    """Fetch trending topics from the X API v1.1 trends endpoint."""

    API_URL = "https://api.twitter.com/1.1/trends/place.json"

    def __init__(
        self,
        bearer_token: Optional[str],
        *,
        woeid: int = 1,
        weight: float = 1.0,
    ) -> None:
        super().__init__("X", weight=weight)
        self._token = bearer_token
        self._woeid = woeid

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        if not self._token:
            raise RuntimeError("X API bearer token is required")

        params = {"id": self._woeid}
        url = f"{self.API_URL}?{parse.urlencode(params)}"
        headers = {"Authorization": f"Bearer {self._token}"}
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._fetch_json, url, headers)
        results: Iterable[Dict[str, Any]] = data[0].get("trends", []) if data else []
        signals: List[TrendSignal] = []
        for entry in results:
            name = entry.get("name") or entry.get("query")
            tweet_volume = entry.get("tweet_volume") or 0
            metadata = {
                "url": entry.get("url"),
                "query": entry.get("query"),
                "promoted_content": entry.get("promoted_content"),
            }
            demographics = [DemographicSlice(label="global", value=100.0)]
            signals.append(
                TrendSignal(
                    term=name or "Unknown",
                    platform=self.name,
                    raw_score=float(tweet_volume or 0),
                    category="social",
                    demographics=demographics,
                    metadata=metadata,
                    url=entry.get("url"),
                )
            )
        return signals

    @staticmethod
    def _fetch_json(url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        LOGGER.debug("Requesting X trends: %s", url)
        req = request.Request(url, headers=headers)  # type: ignore[arg-type]
        with request.urlopen(req, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        return json.loads(payload)
