"""Spotify charts provider."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from urllib import parse, request

from ..models import DemographicSlice, TrendSignal
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


class SpotifyTrendsProvider(TrendProvider):
    """Fetch trending tracks from Spotify playlists."""

    PLAYLISTS = {
        "global": "37i9dQZEVXbMDoHDwVN2tF",
        "us": "37i9dQZEVXbLRQDuF5jeBp",
        "gb": "37i9dQZEVXbLnolsZ8PSNw",
        "ca": "37i9dQZEVXbKj23U1GF4IR",
    }

    def __init__(
        self,
        access_token: Optional[str],
        *,
        market: str = "global",
        playlist_id: Optional[str] = None,
        limit: int = 50,
        weight: float = 1.0,
    ) -> None:
        super().__init__("Spotify", weight=weight)
        self._token = access_token
        self._market = market.lower()
        self._playlist = playlist_id or self.PLAYLISTS.get(self._market, self.PLAYLISTS["global"])
        self._limit = limit

    async def fetch_trends(self) -> Sequence[TrendSignal]:
        if not self._token:
            raise RuntimeError("Spotify access token is required")

        params = {
            "market": self._market.upper(),
            "fields": "items(track(name,artists(name),popularity,album(name,release_date)))",
            "limit": self._limit,
        }
        url = f"https://api.spotify.com/v1/playlists/{self._playlist}/tracks?{parse.urlencode(params)}"
        headers = {"Authorization": f"Bearer {self._token}"}
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._fetch_json, url, headers)
        items: Sequence[Dict[str, Any]] = data.get("items", [])
        signals: List[TrendSignal] = []
        for index, item in enumerate(items, start=1):
            track = item.get("track", {})
            name = track.get("name")
            artists = ", ".join(artist.get("name") for artist in track.get("artists", []) if artist.get("name"))
            album = track.get("album", {}).get("name")
            release_date = track.get("album", {}).get("release_date")
            popularity = float(track.get("popularity", max(0, self._limit - index)))
            metadata = {
                "artist": artists,
                "album": album,
                "release_date": release_date,
            }
            demographics = [DemographicSlice(label=self._market.upper(), value=100.0)]
            signals.append(
                TrendSignal(
                    term=name or "Unknown",
                    platform=self.name,
                    raw_score=popularity,
                    category="music",
                    demographics=demographics,
                    metadata=metadata,
                    url=track.get("external_urls", {}).get("spotify"),
                    region=self._market.upper(),
                )
            )
        return signals

    @staticmethod
    def _fetch_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        LOGGER.debug("Requesting Spotify data: %s", url)
        req = request.Request(url, headers=headers)  # type: ignore[arg-type]
        with request.urlopen(req, timeout=10) as response:  # type: ignore[arg-type]
            payload = response.read().decode("utf-8")
        return json.loads(payload)
