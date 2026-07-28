"""
finverse.ml.earnings_surprise
==============================
Predict beat/miss probability before earnings releases.
Combines historical surprise patterns, revision momentum, earnings quality,
and macro regime context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from finverse.ml.surprise_model import (
    build_features,
    predict_beat_probability,
    extract_historical_surprises,
)
from finverse.ml.revision_tracker import compute_revision_momentum, classify_momentum


@dataclass
class EarningsSurpriseResult:
    ticker: str
    beat_probability: float
    miss_probability: float
    surprise_score_percentile: float
    historical_beat_rate: float
    avg_surprise_magnitude: float
    revision_momentum: float
    implied_move_pct: float | None
    historical_move_pct: float | None
    edge_ratio: float | None
    macro_headwind: str
    confidence: str

    _revision_label: str = field(default="", repr=False)

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            beat_color = "green" if self.beat_probability > 0.60 else "red" if self.beat_probability < 0.45 else "yellow"
            t = Table(title=f"Earnings Surprise Analysis - {self.ticker}")
            t.add_column("Metric", style="bold cyan")
            t.add_column("Value", justify="right")
            t.add_row("Beat Probability", f"[{beat_color}]{self.beat_probability:.1%}[/{beat_color}]")
            t.add_row("Miss Probability", f"{self.miss_probability:.1%}")
            t.add_row("Sector Percentile", f"{self.surprise_score_percentile:.0f}th")
            t.add_row("Historical Beat Rate", f"{self.historical_beat_rate:.1%}")
            t.add_row("Avg Surprise Magnitude", f"{self.avg_surprise_magnitude:+.1%}")
            t.add_row("Revision Momentum", f"{self.revision_momentum:+.2f}  ({self._revision_label})")
            t.add_row("Macro Headwind", self.macro_headwind)
            t.add_row("Confidence", self.confidence)
            console.print(t)
        except ImportError:
            print(f"Earnings Surprise [{self.ticker}]: beat_prob={self.beat_probability:.1%}  beat_rate={self.historical_beat_rate:.1%}")


@dataclass
class EarningsSurpriseBatch:
    results: list
    sector: str

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            sorted_results = sorted(self.results, key=lambda r: r.beat_probability, reverse=True)
            t = Table(title=f"Earnings Surprise Screen - {self.sector.title()} Sector (top {len(sorted_results)})")
            t.add_column("Ticker", style="bold")
            t.add_column("Beat Prob", justify="right")
            t.add_column("Percentile", justify="right")
            t.add_column("Revision")
            t.add_column("Macro")
            t.add_column("Confidence")
            for r in sorted_results:
                c = "green" if r.beat_probability > 0.60 else "red" if r.beat_probability < 0.45 else "yellow"
                t.add_row(
                    r.ticker,
                    f"[{c}]{r.beat_probability:.1%}[/{c}]",
                    f"{r.surprise_score_percentile:.0f}th",
                    r._revision_label[:20],
                    r.macro_headwind,
                    r.confidence,
                )
            console.print(t)
        except ImportError:
            for r in sorted(self.results, key=lambda x: x.beat_probability, reverse=True):
                print(f"{r.ticker}: {r.beat_probability:.1%}")


def _get_historical_earnings_move(data: Any) -> float | None:
    try:
        import yfinance as yf
        ticker = getattr(data, "ticker", str(data))
        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period="2y")
        if hist.empty:
            return None
        daily_ret = hist["Close"].pct_change().abs()
        return float(daily_ret.quantile(0.95))
    except Exception:
        return None


def _get_implied_move_from_chain(chain: Any, data: Any) -> float | None:
    try:
        if chain is None:
            return None
        spot = chain.spot
        exps = chain.expirations
        if not exps:
            return None
        first_exp = exps[0]
        if chain.calls.empty or "expiry" not in chain.calls.columns:
            return None
        calls = chain.calls[chain.calls["expiry"] == first_exp]
        puts = chain.puts[chain.puts["expiry"] == first_exp] if not chain.puts.empty else None
        if calls.empty:
            return None
        calls = calls.copy()
        calls["moneyness"] = abs(calls["strike"] - spot)
        atm_call = calls.loc[calls["moneyness"].idxmin()]
        straddle = float(atm_call.get("lastPrice", 0))
        if puts is not None and not puts.empty and "strike" in puts.columns:
            puts = puts.copy()
            puts["moneyness"] = abs(puts["strike"] - spot)
            atm_put = puts.loc[puts["moneyness"].idxmin()]
            straddle += float(atm_put.get("lastPrice", 0))
        return straddle / spot if spot > 0 else None
    except Exception:
        return None


def _regime_to_headwind(regime_result) -> str:
    if regime_result is None:
        return "MEDIUM"
    try:
        regime = str(getattr(regime_result, "current_regime", "")).lower()
        if hasattr(regime_result.current_regime, "value"):
            regime = str(regime_result.current_regime.value).lower()
    except Exception:
        return "MEDIUM"
    if "expansion" in regime or "recovery" in regime:
        return "LOW"
    if "stress" in regime or "contraction" in regime:
        return "HIGH"
    return "MEDIUM"


def _compute_percentile(beat_prob: float, beat_rate: float) -> float:
    import numpy as np
    mean_prob = 0.55
    std_prob = 0.12
    z = (beat_prob - mean_prob) / std_prob
    from scipy.stats import norm
    return float(norm.cdf(z) * 100)


def _confidence_from_history(n_quarters: int, surprises) -> str:
    if n_quarters >= 12 and len(surprises) >= 8:
        return "HIGH"
    if n_quarters >= 6 or len(surprises) >= 4:
        return "MEDIUM"
    return "LOW"


def analyze(
    data: Any,
    quarters: int = 12,
    sector_peers: bool = True,
    options_chain: Any | None = None,
    regime_result: Any | None = None,
) -> EarningsSurpriseResult:
    ticker = getattr(data, "ticker", str(data))
    surprises = extract_historical_surprises(data)[:quarters]
    n_hist = len(surprises)
    beat_rate = sum(1 for s in surprises if s > 0) / n_hist if n_hist > 0 else 0.55
    avg_magnitude = sum(surprises) / n_hist if n_hist > 0 else 0.0
    revision = compute_revision_momentum(data)
    revision_label = classify_momentum(revision)
    eq_score = None
    try:
        from finverse.audit import earnings_quality
        eq_result = earnings_quality.score(data)
        eq_score = getattr(eq_result, "score", None)
    except Exception:
        pass
    macro_headwind = _regime_to_headwind(regime_result)
    regime_str = "expansion" if macro_headwind == "LOW" else "stress" if macro_headwind == "HIGH" else "slowdown"
    features = build_features(
        historical_surprises=surprises,
        revision_momentum=revision,
        earnings_quality_score=eq_score,
        regime_context=regime_str,
        implied_move=None,
        historical_move=None,
    )
    beat_prob = predict_beat_probability(features)
    implied_move = None
    hist_move = _get_historical_earnings_move(data)
    edge_ratio = None
    if options_chain is not None:
        implied_move = _get_implied_move_from_chain(options_chain, data)
        if implied_move is not None and hist_move is not None and hist_move > 0:
            edge_ratio = implied_move / hist_move
    percentile = _compute_percentile(beat_prob, beat_rate)
    confidence = _confidence_from_history(quarters, surprises)
    return EarningsSurpriseResult(
        ticker=ticker,
        beat_probability=beat_prob,
        miss_probability=1.0 - beat_prob,
        surprise_score_percentile=percentile,
        historical_beat_rate=beat_rate,
        avg_surprise_magnitude=avg_magnitude,
        revision_momentum=revision,
        implied_move_pct=implied_move,
        historical_move_pct=hist_move,
        edge_ratio=edge_ratio,
        macro_headwind=macro_headwind,
        confidence=confidence,
        _revision_label=revision_label,
    )


SECTOR_TICKERS = {
    "tech": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN", "AMD", "INTC",
             "ORCL", "CRM", "ADBE", "QCOM", "AVGO", "TXN", "MU", "AMAT",
             "KLAC", "LRCX", "SNPS", "CDNS"],
    "finance": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "AXP",
                "USB", "PNC", "TFC", "SCHW", "COF", "BK", "STT",
                "FITB", "KEY", "RF", "HBAN", "CFG"],
    "healthcare": ["JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "ABT", "TMO",
                   "DHR", "BMY", "AMGN", "GILD", "CVS", "CI", "HUM",
                   "BIIB", "REGN", "VRTX", "MRNA", "ZTS"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "VLO",
               "PSX", "HAL", "DVN", "FANG", "OXY", "APA", "HES",
               "MRO", "WMB", "KMI", "OKE", "LNG"],
}


class _MinimalTickerData:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.price_history = None
        self.sector = ""


def screen(
    sector: str = "tech",
    top_n: int = 20,
    regime_result: Any | None = None,
) -> EarningsSurpriseBatch:
    tickers = SECTOR_TICKERS.get(sector.lower(), SECTOR_TICKERS["tech"])[:top_n]
    results = []
    for ticker in tickers:
        try:
            data_obj = _MinimalTickerData(ticker)
            result = analyze(data_obj, quarters=12, sector_peers=False, regime_result=regime_result)
            results.append(result)
        except Exception:
            continue
    return EarningsSurpriseBatch(results=results, sector=sector)
