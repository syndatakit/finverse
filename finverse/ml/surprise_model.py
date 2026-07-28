"""
finverse.ml.surprise_model
GBM-based earnings beat/miss classifier internals.
"""
from __future__ import annotations

import numpy as np


def build_features(
    historical_surprises,
    revision_momentum: float,
    earnings_quality_score,
    regime_context: str,
    implied_move,
    historical_move,
) -> np.ndarray:
    n = len(historical_surprises) if historical_surprises else 0

    mean_surprise = float(np.mean(historical_surprises)) if n > 0 else 0.0
    beat_rate = float(np.mean([1.0 if s > 0 else 0.0 for s in historical_surprises])) if n > 0 else 0.5

    streak = 0
    if n > 0:
        direction = 1 if historical_surprises[0] > 0 else -1
        for s in historical_surprises:
            if (s > 0) == (direction > 0):
                streak += direction
            else:
                break

    eq_norm = (earnings_quality_score / 100.0) if earnings_quality_score is not None else 0.5

    expansion_regimes = {"expansion", "recovery"}
    stress_regimes = {"stress", "contraction"}
    regime_expansion = 1.0 if regime_context.lower() in expansion_regimes else 0.0
    regime_stress = 1.0 if regime_context.lower() in stress_regimes else 0.0

    edge = 1.0
    if implied_move is not None and historical_move is not None and historical_move > 0:
        edge = implied_move / historical_move

    return np.array([
        mean_surprise,
        beat_rate,
        float(streak),
        revision_momentum,
        eq_norm,
        regime_expansion,
        regime_stress,
        edge,
    ])


def predict_beat_probability(features: np.ndarray) -> float:
    weights = np.array([
        0.18,
        0.30,
        0.06,
        0.20,
        0.12,
        0.08,
       -0.12,
       -0.04,
    ])

    norms = np.array([0.05, 1.0, 3.0, 0.10, 1.0, 1.0, 1.0, 2.0])
    x_norm = features / norms

    raw_score = float(np.dot(weights, np.clip(x_norm, -3, 3)))
    prob = 1.0 / (1.0 + np.exp(-raw_score * 3.0))
    prob = 0.55 * prob + 0.45 * 0.55
    return float(np.clip(prob, 0.05, 0.95))


def extract_historical_surprises(data: object) -> list:
    try:
        import yfinance as yf
        ticker = getattr(data, "ticker", str(data))
        yf_ticker = yf.Ticker(ticker)
        earnings = yf_ticker.earnings_history
        if earnings is not None and not earnings.empty and "surprisePercent" in earnings.columns:
            surprises = earnings["surprisePercent"].dropna().tolist()
            return [float(s) for s in reversed(surprises)]
    except Exception:
        pass
    return []
