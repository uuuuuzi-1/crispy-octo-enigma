"""Meta (Facebook and Instagram) trend provider using CrowdTangle."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib import parse, request

from ..models import DemographicSlice, TrendSignal
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


class CrowdTangleProvider(TrendProvider):
    """Fetch high-performing social content from the CrowdTangle API."""

    API_URL = "https://api.crowdtangle.com/posts/search"

    def __init__(
        self,
        access_token: Optional[str],
        *,
        timeframe: str = "1h",
        platforms: Sequence[str] = ("facebook", "instagram"),
        sort_by: str = "total_interactions",
        query: Optional[str] = None,
        weight: float = 0.9,
        limit: int = 20,
    ) -> None:
        super().__init__("Meta", weight=weight)
        self._token = access_token
        self._timeframe = timeframe
        self._platforms = platforms
        self._sort_by = sort_by
        self._query = query
        self._limit = limit

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        if not self._token:
            raise RuntimeError("CrowdTangle access token is required")

        params = {
            "token": self._token,
            "sortBy": self._sort_by,
            "timeframe": self._timeframe,
            "count": self._limit,
            "platforms": ",".join(self._platforms),
        }
        if self._query:
            params["searchTerm"] = self._query
        url = f"{self.API_URL}?{parse.urlencode(params)}"
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._fetch_json, url)
        posts: Iterable[Dict[str, Any]] = data.get("result", {}).get("posts", [])
        signals: List[TrendSignal] = []
        for post in posts:
            account = post.get("account", {})
            platform = account.get("platform", "meta")
            title = post.get("title") or post.get("message") or account.get("name")
            statistics = post.get("statistics", {}).get("actual", {})
            interactions = float(statistics.get("total_interactions", 0))
            metadata = {
                "account_name": account.get("name"),
                "account_handle": account.get("handle"),
                "platform": platform,
                "type": post.get("type"),
                "link": post.get("link"),
            }
            demographics = [DemographicSlice(label=platform, value=100.0)]
            signals.append(
                TrendSignal(
                    term=title or "Untitled",
                    platform=self.name,
                    raw_score=interactions,
                    category="social",
                    demographics=demographics,
                    metadata=metadata,
                    url=post.get("link"),
                )
            )
        return signals

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        LOGGER.debug("Requesting CrowdTangle data: %s", url)
        with request.urlopen(url, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        return json.loads(payload)
