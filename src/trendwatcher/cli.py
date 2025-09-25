"""Command line interface for the TrendWatcher toolkit."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import List

from .aggregator import TrendAggregator
from .models import DemographicSlice, TrendSignal
from .providers import SampleProvider
from .providers.base import TrendProvider
from .providers.registry import load_default_providers

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform trend analysis")
    parser.add_argument("--interval", type=float, default=0.0, help="Polling interval for continuous updates")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--samples", action="store_true", help="Use built-in sample data")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser


async def _collect_once(aggregator: TrendAggregator, *, as_json: bool) -> None:
    report = await aggregator.collect_once()
    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Report generated at {report.generated_at.isoformat()} with {len(report.trends)} trends")
        for trend in report.trends:
            categories = ", ".join(trend.categories)
            demo = ", ".join(f"{d.label} {d.value:.1f}%" for d in trend.demographics[:3]) or "n/a"
            print(f"- {trend.term}: score={trend.score:.1f} categories={categories} demographics={demo}")
            print(f"  {trend.narrative}")


async def run_async(args: argparse.Namespace) -> None:
    providers = _build_providers(args.samples)
    if not providers:
        raise RuntimeError("No providers are configured. Set API keys or use --samples.")

    aggregator = TrendAggregator(providers)
    if args.interval > 0:
        async for report in aggregator.stream(args.interval):
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(f"Report generated at {report.generated_at.isoformat()} with {len(report.trends)} trends")
                for trend in report.trends:
                    categories = ", ".join(trend.categories)
                    demo = ", ".join(f"{d.label} {d.value:.1f}%" for d in trend.demographics[:3]) or "n/a"
                    print(f"- {trend.term}: score={trend.score:.1f} categories={categories} demographics={demo}")
                    print(f"  {trend.narrative}")
    else:
        await _collect_once(aggregator, as_json=args.json)


def _build_providers(use_samples: bool) -> List[TrendProvider]:
    if use_samples:
        sample_signals = [
            TrendSignal(
                term="Aurora Skies",
                platform="YouTube",
                raw_score=92,
                category="music",
                demographics=[DemographicSlice(label="18-24", value=60), DemographicSlice(label="Female", value=55)],
                metadata={"keywords": ["pop", "live"], "description": "Viral live performance clip."},
            ),
            TrendSignal(
                term="Aurora Skies",
                platform="Spotify",
                raw_score=88,
                category="music",
                demographics=[DemographicSlice(label="US", value=70), DemographicSlice(label="Global", value=40)],
                metadata={"artist": "DJ Nova"},
            ),
            TrendSignal(
                term="City Marathon",
                platform="X",
                raw_score=65,
                category="sports",
                demographics=[DemographicSlice(label="Male", value=52), DemographicSlice(label="25-34", value=48)],
                metadata={"keywords": ["running", "marathon"]},
            ),
        ]
        return [
            SampleProvider("YouTube", [sample_signals[0]]),
            SampleProvider("Spotify", [sample_signals[1]]),
            SampleProvider("X", [sample_signals[2]]),
        ]

    return list(load_default_providers())


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        asyncio.run(run_async(args))
    except KeyboardInterrupt:
        LOGGER.info("Stopping TrendWatcher")


if __name__ == "__main__":
    main()
