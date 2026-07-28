"""
finverse.ml.price_target_ensemble
===================================
ML-weighted ensemble of valuation signals into a single price target
with confidence intervals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finverse.ml.ensemble_weights import (
    get_weights,
    compute_ensemble,
    signal_agreement,
    compute_confidence_intervals,
)


@dataclass
class PriceTargetResult:
    ticker: str
    current_price: float
    ensemble_target: float
    upside_pct: float
    confidence_interval_80: tuple
    confidence_interval_95: tuple
    dcf_target: float | None
    comps_target: float | None
    momentum_target: float | None
    consensus_target: float | None
    weights: dict
    signal_agreement: str
    rating: str

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            upside_color = "green" if self.upside_pct > 0.10 else "red" if self.upside_pct < -0.10 else "yellow"
            rating_color = "green" if self.rating == "BUY" else "red" if self.rating == "SELL" else "yellow"
            t = Table(title=f"Price Target Ensemble - {self.ticker}")
            t.add_column("Metric", style="bold cyan")
            t.add_column("Value", justify="right")
            t.add_row("Current Price", f"${self.current_price:.2f}")
            t.add_row("Ensemble Target", f"${self.ensemble_target:.2f}")
            t.add_row("Upside / Downside", f"[{upside_color}]{self.upside_pct:+.1%}[/{upside_color}]")
            t.add_row("Rating", f"[{rating_color}]{self.rating}[/{rating_color}]")
            t.add_row("Signal Agreement", self.signal_agreement)
            t.add_row("80% CI", f"${self.confidence_interval_80[0]:.2f} - ${self.confidence_interval_80[1]:.2f}")
            t.add_row("95% CI", f"${self.confidence_interval_95[0]:.2f} - ${self.confidence_interval_95[1]:.2f}")
            t.add_row("--- Signal Breakdown ---", "")
            signals = [
                ("DCF Target", self.dcf_target, self.weights.get("dcf", 0)),
                ("Comps Target", self.comps_target, self.weights.get("comps", 0)),
                ("Momentum Target", self.momentum_target, self.weights.get("momentum", 0)),
                ("Consensus Target", self.consensus_target, self.weights.get("consensus", 0)),
            ]
            for name, val, wt in signals:
                if val is not None:
                    t.add_row(f"  {name} (w={wt:.0%})", f"${val:.2f}")
                else:
                    t.add_row(f"  {name}", "N/A")
            console.print(t)
        except ImportError:
            print(f"Price Target [{self.ticker}]: target=${self.ensemble_target:.2f}  upside={self.upside_pct:+.1%}  rating={self.rating}")


def _get_current_price(data: Any) -> float:
    if hasattr(data, "price_history") and data.price_history is not None and not data.price_history.empty:
        return float(data.price_history["Close"].iloc[-1])
    try:
        import yfinance as yf
        ticker = getattr(data, "ticker", str(data))
        info = yf.Ticker(ticker).fast_info
        return float(info.get("last_price", 100.0))
    except Exception:
        return 100.0


def _get_dcf_target(data: Any, dcf_model):
    if dcf_model is not None:
        return getattr(dcf_model, "implied_price", None)
    try:
        from finverse import DCF
        model = DCF(data).use_ml_forecast().run()
        return getattr(model, "implied_price", None)
    except Exception:
        return None


def _get_comps_target(data: Any, peers):
    try:
        from finverse import comps as comps_fn
        result = comps_fn(data, peers=peers) if peers else comps_fn(data)
        lo = getattr(result, "price_low", None)
        hi = getattr(result, "price_high", None)
        mid = getattr(result, "implied_price", None)
        if mid is not None:
            return float(mid)
        if lo is not None and hi is not None:
            return (float(lo) + float(hi)) / 2
    except Exception:
        pass
    return None


def _get_momentum_target(data: Any, current_price: float):
    try:
        if hasattr(data, "price_history") and data.price_history is not None:
            closes = data.price_history["Close"]
            if len(closes) >= 252:
                mom_return = float(closes.iloc[-22] / closes.iloc[-252] - 1)
                projected_return = mom_return * 0.5
                return current_price * (1 + projected_return)
    except Exception:
        pass
    return None


def _get_consensus_target(data: Any):
    try:
        import yfinance as yf
        ticker = getattr(data, "ticker", str(data))
        info = yf.Ticker(ticker).analyst_price_targets
        if info and "mean" in info:
            return float(info["mean"])
    except Exception:
        pass
    return None


def _get_sector(data: Any) -> str:
    if hasattr(data, "sector"):
        return (data.sector or "").lower()
    try:
        import yfinance as yf
        ticker = getattr(data, "ticker", str(data))
        info = yf.Ticker(ticker).info
        return info.get("sector", "").lower()
    except Exception:
        return "default"


def _derive_rating(upside: float, agreement: str) -> str:
    if upside > 0.15 and agreement in ("HIGH", "MEDIUM"):
        return "BUY"
    if upside < -0.10 and agreement in ("HIGH", "MEDIUM"):
        return "SELL"
    if upside > 0.25:
        return "BUY"
    if upside < -0.20:
        return "SELL"
    return "HOLD"


def analyze(
    data: Any,
    peers=None,
    dcf_model=None,
    regime_result=None,
) -> PriceTargetResult:
    ticker = getattr(data, "ticker", str(data))
    current_price = _get_current_price(data)
    regime_str = "expansion"
    if regime_result is not None:
        try:
            regime_str = str(
                regime_result.current_regime.value
                if hasattr(regime_result.current_regime, "value")
                else regime_result.current_regime
            ).lower()
        except Exception:
            pass
    sector = _get_sector(data)
    dcf_target = _get_dcf_target(data, dcf_model)
    comps_target = _get_comps_target(data, peers)
    momentum_target = _get_momentum_target(data, current_price)
    consensus_target = _get_consensus_target(data)
    targets = {
        "dcf": dcf_target,
        "comps": comps_target,
        "momentum": momentum_target,
        "consensus": consensus_target,
    }
    weights = get_weights(
        sector=sector,
        regime=regime_str,
        has_consensus=consensus_target is not None,
    )
    ensemble = compute_ensemble(targets, weights)
    if ensemble == 0.0:
        ensemble = current_price
    upside = (ensemble - current_price) / current_price if current_price > 0 else 0.0
    agreement = signal_agreement(targets, ensemble)
    ci_80, ci_95 = compute_confidence_intervals(targets, ensemble)
    rating = _derive_rating(upside, agreement)
    return PriceTargetResult(
        ticker=ticker,
        current_price=current_price,
        ensemble_target=round(ensemble, 2),
        upside_pct=upside,
        confidence_interval_80=(round(ci_80[0], 2), round(ci_80[1], 2)),
        confidence_interval_95=(round(ci_95[0], 2), round(ci_95[1], 2)),
        dcf_target=round(dcf_target, 2) if dcf_target else None,
        comps_target=round(comps_target, 2) if comps_target else None,
        momentum_target=round(momentum_target, 2) if momentum_target else None,
        consensus_target=round(consensus_target, 2) if consensus_target else None,
        weights=weights,
        signal_agreement=agreement,
        rating=rating,
    )
