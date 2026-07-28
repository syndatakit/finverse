"""
finverse.derivatives.rates
==========================
Interest rate derivatives: fixed/float swaps, FRAs, and European swaptions.
Integrates with finverse.macro.nelson_siegel for discount factors.

Usage
-----
from finverse.derivatives import rates
from finverse.macro import nelson_siegel

curve = nelson_siegel.us_curve()

swap = rates.swap(notional=10_000_000, fixed_rate=0.045, tenor=5,
                  payment_freq='semi-annual', curve=curve)
swap.summary()
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from finverse.derivatives.discount import (
    discount_factor,
    forward_rate,
    par_swap_rate,
    annuity_pv,
)
from finverse.derivatives.blacks_model import blacks_swaption


PaymentFreq = Literal["annual", "semi-annual", "quarterly", "monthly"]
SwaptionType = Literal["payer", "receiver"]


@dataclass
class SwapResult:
    notional: float
    fixed_rate: float
    tenor: float
    payment_freq: str

    npv: float = 0.0
    par_swap_rate: float = 0.0
    dv01: float = 0.0
    fixed_leg_pv: float = 0.0
    float_leg_pv: float = 0.0
    cash_flows: pd.DataFrame = field(default_factory=pd.DataFrame)
    breakeven_shift: float = 0.0

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            t = Table(title=f"Interest Rate Swap  notional={self.notional:,.0f}  tenor={self.tenor}y  freq={self.payment_freq}")
            t.add_column("Metric", style="bold cyan")
            t.add_column("Value", justify="right")
            t.add_row("Fixed Rate", f"{self.fixed_rate:.3%}")
            t.add_row("Par Swap Rate", f"{self.par_swap_rate:.3%}")
            t.add_row("NPV (fixed payer)", f"${self.npv:,.2f}")
            t.add_row("Fixed Leg PV", f"${self.fixed_leg_pv:,.2f}")
            t.add_row("Float Leg PV", f"${self.float_leg_pv:,.2f}")
            t.add_row("DV01", f"${self.dv01:,.2f}")
            t.add_row("Breakeven Shift", f"{self.breakeven_shift:+.1f} bps")
            console.print(t)
        except ImportError:
            print(f"Swap NPV={self.npv:,.2f}  par_rate={self.par_swap_rate:.3%}  DV01={self.dv01:,.2f}")


def swap(
    notional: float,
    fixed_rate: float,
    tenor: float,
    payment_freq: PaymentFreq = "semi-annual",
    curve: Any | None = None,
) -> SwapResult:
    freq_map = {"annual": 1, "semi-annual": 2, "quarterly": 4, "monthly": 12}
    n_per_year = freq_map.get(payment_freq, 2)
    dt = 1 / n_per_year
    n_periods = int(tenor * n_per_year)
    from finverse.derivatives.discount import par_swap_rate as _psr
    flat_rate = _psr(tenor, payment_freq) if curve is None else fixed_rate

    rows = []
    fixed_pv = 0.0
    float_pv = 0.0

    for i in range(1, n_periods + 1):
        t = i * dt
        P_t = discount_factor(t, curve, flat_rate)
        fwd = forward_rate(t - dt, t, curve, flat_rate)

        fixed_cf = notional * fixed_rate * dt
        float_cf = notional * fwd * dt

        fixed_pv += fixed_cf * P_t
        float_pv += float_cf * P_t

        rows.append({
            "period": i,
            "payment_date_y": round(t, 4),
            "discount_factor": round(P_t, 6),
            "forward_rate": round(fwd, 6),
            "fixed_cashflow": round(fixed_cf, 2),
            "float_cashflow": round(float_cf, 2),
            "fixed_pv": round(fixed_cf * P_t, 2),
            "float_pv": round(float_cf * P_t, 2),
        })

    npv = float_pv - fixed_pv
    psr = par_swap_rate(tenor, payment_freq, curve, flat_rate)

    fixed_pv_up = sum(
        notional * fixed_rate * dt * discount_factor(i * dt, None, flat_rate + 0.0001)
        for i in range(1, n_periods + 1)
    )
    float_pv_up = sum(
        notional * forward_rate((i - 1) * dt, i * dt, None, flat_rate + 0.0001) * dt
        * discount_factor(i * dt, None, flat_rate + 0.0001)
        for i in range(1, n_periods + 1)
    )
    npv_up = float_pv_up - fixed_pv_up
    dv01 = abs(npv_up - npv)

    breakeven_shift = (psr - fixed_rate) * 10000 if dv01 > 0 else 0.0

    return SwapResult(
        notional=notional,
        fixed_rate=fixed_rate,
        tenor=tenor,
        payment_freq=payment_freq,
        npv=npv,
        par_swap_rate=psr,
        dv01=dv01,
        fixed_leg_pv=fixed_pv,
        float_leg_pv=float_pv,
        cash_flows=pd.DataFrame(rows),
        breakeven_shift=breakeven_shift,
    )


@dataclass
class FRAResult:
    notional: float
    contract_rate: float
    start: float
    end: float

    npv: float = 0.0
    implied_forward_rate: float = 0.0
    settlement_amount: float = 0.0

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            t = Table(title=f"Forward Rate Agreement  notional={self.notional:,.0f}")
            t.add_column("Metric", style="bold cyan")
            t.add_column("Value", justify="right")
            t.add_row("Contract Rate", f"{self.contract_rate:.3%}")
            t.add_row("Implied Forward Rate", f"{self.implied_forward_rate:.3%}")
            t.add_row("FRA Period", f"{self.start:.2f}y to {self.end:.2f}y")
            t.add_row("NPV", f"${self.npv:,.2f}")
            t.add_row("Settlement Amount (at start)", f"${self.settlement_amount:,.2f}")
            console.print(t)
        except ImportError:
            print(f"FRA NPV={self.npv:,.2f}  fwd_rate={self.implied_forward_rate:.3%}")


def fra(
    notional: float,
    contract_rate: float,
    start: float,
    end: float,
    curve: Any | None = None,
) -> FRAResult:
    dt = end - start
    flat_rate = contract_rate
    fwd = forward_rate(start, end, curve, flat_rate)
    P_end = discount_factor(end, curve, flat_rate)
    P_start = discount_factor(start, curve, flat_rate)

    npv = notional * (fwd - contract_rate) * dt * P_end
    settlement = notional * (fwd - contract_rate) * dt / (1 + fwd * dt)

    return FRAResult(
        notional=notional,
        contract_rate=contract_rate,
        start=start,
        end=end,
        npv=npv,
        implied_forward_rate=fwd,
        settlement_amount=settlement,
    )


@dataclass
class SwaptionResult:
    notional: float
    strike_rate: float
    option_expiry: float
    swap_tenor: float
    vol: float
    swaption_type: str

    price: float = 0.0
    delta: float = 0.0
    vega: float = 0.0
    par_swap_rate: float = 0.0
    breakeven_vol: float = 0.0

    def summary(self) -> None:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            t = Table(title=f"Swaption  {self.swaption_type.upper()}  expiry={self.option_expiry}y  swap={self.swap_tenor}y")
            t.add_column("Metric", style="bold cyan")
            t.add_column("Value", justify="right")
            t.add_row("Strike Rate", f"{self.strike_rate:.3%}")
            t.add_row("Par Swap Rate", f"{self.par_swap_rate:.3%}")
            t.add_row("Black Vol", f"{self.vol:.2%}")
            t.add_row("Price", f"${self.price:,.2f}")
            t.add_row("Delta", f"${self.delta:,.2f}")
            t.add_row("Vega (per 1% vol)", f"${self.vega:,.2f}")
            console.print(t)
        except ImportError:
            print(f"Swaption price={self.price:,.2f}  delta={self.delta:,.2f}")


def swaption(
    notional: float,
    strike_rate: float,
    option_expiry: float,
    swap_tenor: float,
    vol: float,
    curve: Any | None = None,
    type: SwaptionType = "payer",
) -> SwaptionResult:
    flat_rate = strike_rate
    psr = par_swap_rate(swap_tenor, "semi-annual", curve, flat_rate)
    ann = annuity_pv(swap_tenor, "semi-annual", curve, flat_rate)

    result = blacks_swaption(
        notional=notional,
        strike_rate=strike_rate,
        swap_rate=psr,
        annuity=ann,
        vol=vol,
        option_expiry=option_expiry,
        type=type,
    )

    return SwaptionResult(
        notional=notional,
        strike_rate=strike_rate,
        option_expiry=option_expiry,
        swap_tenor=swap_tenor,
        vol=vol,
        swaption_type=type,
        price=result["price"],
        delta=result["delta"],
        vega=result["vega"],
        par_swap_rate=psr,
        breakeven_vol=result["breakeven_vol"],
    )
