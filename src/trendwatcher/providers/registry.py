"""Utilities for creating provider collections from environment settings."""

from __future__ import annotations

import logging
import os
from typing import List, Sequence

from .apple_music import AppleMusicTrendsProvider
from .google import GoogleTrendsProvider, YouTubeTrendsProvider
from .meta import CrowdTangleProvider
from .spotify import SpotifyTrendsProvider
from .x import XTrendsProvider
from .base import TrendProvider

LOGGER = logging.getLogger(__name__)


def load_default_providers() -> Sequence[TrendProvider]:
    """Instantiate providers using configuration from environment variables."""

    providers: List[TrendProvider] = []

    region = os.getenv("TRENDWATCHER_REGION", "US")
    providers.append(GoogleTrendsProvider(region=region))

    youtube_key = os.getenv("YOUTUBE_API_KEY")
    if youtube_key:
        providers.append(YouTubeTrendsProvider(youtube_key, region=region))
    else:
        LOGGER.warning("Skipping YouTube provider: YOUTUBE_API_KEY is not set")

    x_token = os.getenv("X_BEARER_TOKEN")
    if x_token:
        providers.append(XTrendsProvider(x_token, woeid=int(os.getenv("X_WOEID", "1"))))
    else:
        LOGGER.warning("Skipping X provider: X_BEARER_TOKEN is not set")

    apple_token = os.getenv("APPLE_MUSIC_TOKEN")
    if apple_token:
        providers.append(
            AppleMusicTrendsProvider(
                apple_token,
                storefront=os.getenv("APPLE_MUSIC_STOREFRONT", region.lower()),
            )
        )
    else:
        LOGGER.warning("Skipping Apple Music provider: APPLE_MUSIC_TOKEN is not set")

    spotify_token = os.getenv("SPOTIFY_TOKEN")
    if spotify_token:
        providers.append(
            SpotifyTrendsProvider(
                spotify_token,
                market=os.getenv("SPOTIFY_MARKET", region.lower()),
            )
        )
    else:
        LOGGER.warning("Skipping Spotify provider: SPOTIFY_TOKEN is not set")

    crowdtangle_token = os.getenv("CROWDTANGLE_TOKEN")
    if crowdtangle_token:
        providers.append(CrowdTangleProvider(crowdtangle_token))
    else:
        LOGGER.warning("Skipping CrowdTangle provider: CROWDTANGLE_TOKEN is not set")

    return providers
