# TrendWatcher

TrendWatcher is a cross-platform trend analytics toolkit that combines public and authenticated feeds from Google (Search and YouTube), X (Twitter), Apple Music, Spotify, and Meta (Facebook/Instagram via CrowdTangle) into a single continuously updated view. The toolkit normalises data from each provider, assigns popularity scores, classifies trends by genre, and highlights key demographic segments so that editorial, marketing, and research teams can respond in real time.

## Features

- **Unified aggregation** – Normalises trend data from major search, social, and streaming platforms.
- **Genre inference** – Lightweight keyword-based classifier fills gaps when providers do not supply explicit categories.
- **Demographic weighting** – Combines demographic slices from multiple sources into a single view for each topic.
- **Popularity scoring** – Weighted scoring model aligns metrics with platform influence and applies smoothing to reduce noise.
- **Continuous polling** – Async streaming API and CLI support scheduled updates for real-time dashboards.
- **Extensible providers** – Clear provider interfaces simplify integrating additional social platforms.

## Getting started

The package is published as a standard Python project. Install dependencies (only the Python standard library is required) and make sure you are running Python 3.10 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuring providers

Some providers expose public endpoints while others require authentication tokens. Environment variables are used by default when the CLI is run without the `--samples` flag:

| Provider | Environment variables | Notes |
|----------|----------------------|-------|
| Google Search | `TRENDWATCHER_REGION` (optional) | Uses the public Google Trends real-time endpoint. |
| YouTube | `YOUTUBE_API_KEY` | Requires a YouTube Data API v3 key. |
| X (Twitter) | `X_BEARER_TOKEN`, `X_WOEID` (optional) | Uses the v1.1 trends API. |
| Apple Music | `APPLE_MUSIC_TOKEN`, `APPLE_MUSIC_STOREFRONT` (optional) | Requires a MusicKit developer token. |
| Spotify | `SPOTIFY_TOKEN`, `SPOTIFY_MARKET` (optional) | Provide a valid OAuth access token. |
| Meta / CrowdTangle | `CROWDTANGLE_TOKEN` | Access token from the CrowdTangle API. |

If any token is missing the CLI will skip that provider and log a warning.

## Command line usage

The CLI offers a simple way to inspect the combined report:

```bash
python -m trendwatcher.cli --samples
```

Use real APIs by exporting the relevant environment variables and running without `--samples`:

```bash
export YOUTUBE_API_KEY=your-key
export X_BEARER_TOKEN=your-token
export SPOTIFY_TOKEN=your-token
export APPLE_MUSIC_TOKEN=your-token
export CROWDTANGLE_TOKEN=your-token
python -m trendwatcher.cli --interval 300 --json
```

Key options:

- `--interval` – Polling interval in seconds for continuous updates. Omit for a single report.
- `--json` – Emit machine-friendly JSON instead of a textual summary.
- `--samples` – Use built-in simulated providers for demos or testing.
- `--verbose` – Enable debug logging.

## Library usage

```python
import asyncio
from trendwatcher.aggregator import TrendAggregator
from trendwatcher.providers.registry import load_default_providers

async def main() -> None:
    providers = load_default_providers()
    aggregator = TrendAggregator(providers)
    report = await aggregator.collect_once()
    for trend in report.trends:
        print(trend.term, trend.score, trend.categories, trend.narrative)

asyncio.run(main())
```

The `TrendAggregator.stream()` coroutine yields successive reports at a given interval, making it straightforward to drive dashboards or alerting systems.

## Running tests

```bash
pytest
```

## Extending

- **Add providers:** subclass `TrendProvider` and return `TrendSignal` instances. The aggregator automatically combines scores using provider weights.
- **Custom scoring:** adjust weights when instantiating providers or override the aggregator to implement bespoke scoring functions.
- **Advanced classification:** supply a custom `GenreClassifier` with richer heuristics or ML-backed categorisation.

## Caveats

- Some APIs enforce strict rate limits and require authentication. Handle credential storage securely.
- Real-time data sources may change format; provider modules are written defensively but may need updates if upstream schemas evolve.
- Demographic data availability varies by platform and may require additional permissions.
