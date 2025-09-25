"""Tests for the genre classifier heuristics."""

from __future__ import annotations

from trendwatcher.classifier import GenreClassifier
from trendwatcher.models import TrendSignal


def test_classifier_prefers_explicit_metadata() -> None:
    signal = TrendSignal(term="Test", platform="Unit", raw_score=10, metadata={"genre": "custom"})
    classifier = GenreClassifier()
    assert classifier.classify(signal) == "custom"


def test_classifier_keyword_detection() -> None:
    signal = TrendSignal(term="NBA finals highlights", platform="X", raw_score=20)
    classifier = GenreClassifier()
    assert classifier.classify(signal) == "sports"


def test_classifier_default_genre() -> None:
    signal = TrendSignal(term="Completely novel concept", platform="Meta", raw_score=5)
    classifier = GenreClassifier(default_genre="other")
    assert classifier.classify(signal) == "other"
