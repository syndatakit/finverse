"""
finverse - The ML-powered financial modeling toolkit.
v0.8.0 - Refactor pass: deprecation shim for legacy flat-name imports,
         canonical paths documented in MIGRATION.md.
"""
__version__ = "0.8.0"
__author__ = "finverse"

# Canonical public API
# Use the subpackage paths as the canonical surface.  Flat aliases for the
# legacy top-level names (DCF, LBO, comps, option_call, option_put, bond_price,
# ytm_from_price, etc.) are provided via `finverse._compat` and emit
# DeprecationWarning.  New code should import from the subpackages directly.
from finverse import (  # noqa: E402
    pull, ml, risk, screen, backtest, portfolio, audit, credit, valuation,
    macro, options, derivatives, analysis,
)

# Compatibility shim (deprecated, scheduled for removal in v1.0.0)
from finverse._compat import (  # noqa: E402, F401
    DCF, LBO, ThreeStatement, comps,
    ddm_gordon, h_model, ddm_multistage,
    sotp, Segment, regime_dcf, synthetic_peers,
    option_call, option_put, bond_price, ytm_from_price,
)

# Convenience re-exports at the top level (not deprecated)
from finverse.analysis.sensitivity import sensitivity
from finverse.analysis.scenarios import scenarios

__all__ = [
    # Subpackage handles
    "pull", "ml", "risk", "screen", "backtest", "portfolio",
    "audit", "credit", "valuation", "macro",
    "options", "derivatives", "analysis",

    # Convenience re-exports
    "sensitivity", "scenarios",

    # Deprecated flat names (kept for backwards compatibility)
    "DCF", "LBO", "ThreeStatement", "comps",
    "ddm_gordon", "h_model", "ddm_multistage",
    "sotp", "Segment", "regime_dcf", "synthetic_peers",
    "option_call", "option_put", "bond_price", "ytm_from_price",

    # Metadata
    "__version__",
]
