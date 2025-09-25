"""Google Search and YouTube trend providers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib import parse, request

from ..models import DemographicSlice, TrendSignal
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


class GoogleTrendsClient:
    """Thin wrapper around the public Google Trends endpoints."""

    def __init__(self, *, region: str = "US", hl: str = "en-US", timezone_offset: int = 0) -> None:
        self.region = region
        self.hl = hl
        self.timezone_offset = timezone_offset

    def realtime_trends(self, category: str = "all") -> List[Dict[str, Any]]:
        params = {
            "hl": self.hl,
            "tz": self.timezone_offset,
            "cat": category,
            "fi": 0,
            "fs": 0,
            "geo": self.region,
            "ri": 300,
            "rs": 20,
            "sort": 0,
        }
        url = "https://trends.google.com/trends/api/realtimetrends?" + parse.urlencode(params)
        LOGGER.debug("Requesting Google Trends data: %s", url)
        with request.urlopen(url, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        # The response contains a security preamble that needs to be stripped.
        payload = payload[payload.find("{") :]
        data = json.loads(payload)
        return data.get("storySummaries", {}).get("trendingStories", [])


class GoogleTrendsProvider(TrendProvider):
    """Provider that surfaces real-time Google Search trends."""

    def __init__(
        self,
        *,
        region: str = "US",
        hl: str = "en-US",
        timezone_offset: int = 0,
        weight: float = 1.2,
        client: Optional[GoogleTrendsClient] = None,
    ) -> None:
        super().__init__("Google Search", weight=weight)
        self._client = client or GoogleTrendsClient(region=region, hl=hl, timezone_offset=timezone_offset)
        self._region = region

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        loop = asyncio.get_running_loop()
        stories = await loop.run_in_executor(None, self._client.realtime_trends, "all")
        return [self._story_to_signal(story) for story in stories]

    def _story_to_signal(self, story: Dict[str, Any]) -> TrendSignal:
        entity_names: List[str] = story.get("entityNames", []) or []
        title = story.get("title", {}).get("query") or (entity_names[0] if entity_names else "Unknown")
        share = story.get("shareCount", 0)
        article_summaries = [article.get("title") for article in story.get("articles", [])[:3]]
        metadata: Dict[str, Any] = {
            "keywords": entity_names,
            "articles": [summary for summary in article_summaries if summary],
        }
        if story.get("shareUrl"):
            metadata["share_url"] = story["shareUrl"]
        return TrendSignal(
            term=title,
            platform=self.name,
            raw_score=float(share or 0),
            category=story.get("category"),
            demographics=[],
            metadata=metadata,
            region=self._region,
            url=story.get("shareUrl"),
        )


class YouTubeTrendsProvider(TrendProvider):
    """Provider backed by the YouTube Data API."""

    API_URL = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(
        self,
        api_key: Optional[str],
        *,
        region: str = "US",
        max_results: int = 25,
        weight: float = 1.1,
    ) -> None:
        super().__init__("YouTube", weight=weight)
        self._api_key = api_key
        self._region = region
        self._max_results = max_results

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        if not self._api_key:
            raise RuntimeError("YouTube API key is required for YouTube trends")

        params = {
            "chart": "mostPopular",
            "regionCode": self._region,
            "maxResults": self._max_results,
            "part": "snippet,statistics,topicDetails",
            "key": self._api_key,
        }
        url = f"{self.API_URL}?{parse.urlencode(params)}"
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._fetch_json, url)
        items: Iterable[Dict[str, Any]] = data.get("items", [])
        signals: List[TrendSignal] = []
        for entry in items:
            snippet = entry.get("snippet", {})
            statistics = entry.get("statistics", {})
            topic_details = entry.get("topicDetails", {})
            tags = snippet.get("tags", [])
            category = snippet.get("categoryId")
            view_count = float(statistics.get("viewCount", 0))
            demographics = [
                DemographicSlice(label="global", value=100.0),
            ]
            metadata = {
                "keywords": tags,
                "channel": snippet.get("channelTitle"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "topics": topic_details.get("topicCategories", []),
            }
            signals.append(
                TrendSignal(
                    term=snippet.get("title", "Unknown"),
                    platform=self.name,
                    raw_score=view_count,
                    category=category,
                    demographics=demographics,
                    metadata=metadata,
                    url=f"https://www.youtube.com/watch?v={entry.get('id')}",
                    region=self._region,
                )
            )
        return signals

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        LOGGER.debug("Requesting YouTube data: %s", url)
        with request.urlopen(url, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        return json.loads(payload)
