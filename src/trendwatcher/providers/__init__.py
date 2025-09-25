"""Provider implementations for TrendWatcher."""

from .apple_music import AppleMusicTrendsProvider
from .google import GoogleTrendsProvider, GoogleTrendsClient, YouTubeTrendsProvider
from .meta import CrowdTangleProvider
from .sample import SampleProvider
from .spotify import SpotifyTrendsProvider
from .x import XTrendsProvider

__all__ = [
    "AppleMusicTrendsProvider",
    "CrowdTangleProvider",
    "GoogleTrendsClient",
    "GoogleTrendsProvider",
    "SampleProvider",
    "SpotifyTrendsProvider",
    "XTrendsProvider",
    "YouTubeTrendsProvider",
]
