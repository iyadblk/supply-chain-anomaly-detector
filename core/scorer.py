"""Severity scoring helpers."""
from __future__ import annotations


def severity_band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def severity_color(score: float) -> str:
    band = severity_band(score)
    return {"high": "#FF4B4B", "medium": "#FFB347", "low": "#FFD700"}[band]
