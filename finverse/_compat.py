"""finverse._compat - deprecation shim for legacy flat-name imports.

The legacy top-level imports below were re-exports of internal modules.  As
of v0.8.0 they are aliased here and emit a DeprecationWarning.  New code
should import from the canonical subpackage paths.

Migration map
-------------
Legacy (deprecated)                      Canonical (new)
---------------------------------------  --------------------------------------
from finverse import DCF                  from finverse.models.dcf import DCF
from finverse import LBO                  from finverse.models.lbo import LBO
from finverse import ThreeStatement       from finverse.models.three_statement import ThreeStatement
from finverse import comps                from finverse.models.comps import analyze
from finverse import ddm_gordon           from finverse.models.ddm import gordon
from finverse import h_model              from finverse.models.ddm import h_model
from finverse import ddm_multistage       from finverse.models.ddm import multistage
from finverse import sotp                 from finverse.models.sotp import analyze
from finverse import Segment              from finverse.models.sotp import Segment
from finverse import regime_dcf           from finverse.models.regime_dcf import analyze
from finverse import synthetic_peers      from finverse.models.synthetic_peers import build_peers
from finverse import option_call          from finverse.options.black_scholes import price   # type=call
from finverse import option_put           from finverse.options.black_scholes import price   # type=put
from finverse import bond_price           from finverse.models.bonds import price
from finverse import ytm_from_price       from finverse.models.bonds import ytm_from_price

Removal is scheduled for v1.0.0.
"""

from __future__ import annotations

import warnings
from typing import Any


_DEPRECATION_REMOVE_VERSION = "1.0.0"


def _warn_legacy(name: str, canonical: str) -> None:
    warnings.warn(
        f"`from finverse import {name}` is deprecated as of v0.8.0 and will be "
        f"removed in v{_DEPRECATION_REMOVE_VERSION}.  Use `{canonical}` instead.  "
        f"See MIGRATION.md for the full mapping.",
        DeprecationWarning,
        stacklevel=3,
    )


class _FunctionAlias:
    """Wrap a callable so that calling it emits a DeprecationWarning.

    Importing the alias does NOT fire (matches numpy/pandas convention).
    Attribute access on the alias also does NOT fire - only `__call__` does.
    """

    __slots__ = ("__target", "__name", "__canonical")

    def __init__(self, target: Any, legacy_name: str, canonical_path: str) -> None:
        object.__setattr__(self, "_FunctionAlias__target", target)
        object.__setattr__(self, "_FunctionAlias__name", legacy_name)
        object.__setattr__(self, "_FunctionAlias__canonical", canonical_path)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        _warn_legacy(self.__name, self.__canonical)
        return self.__target(*args, **kwargs)


class _ClassAlias:
    """Wrap a class so that instantiating it emits a DeprecationWarning.

    Importing the alias does NOT fire.  Attribute access (e.g. `DCF.__name__`)
    does NOT fire - only calling the class (i.e. constructing an instance)
    emits the warning.
    """

    __slots__ = ("__target", "__name", "__canonical")

    def __init__(self, target: Any, legacy_name: str, canonical_path: str) -> None:
        object.__setattr__(self, "_ClassAlias__target", target)
        object.__setattr__(self, "_ClassAlias__name", legacy_name)
        object.__setattr__(self, "_ClassAlias__canonical", canonical_path)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        _warn_legacy(self.__name, self.__canonical)
        return self.__target(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.__target, item)

    def __instancecheck__(self, instance: Any) -> bool:
        return isinstance(instance, self.__target)


# Valuation models
from finverse.models.dcf import DCF as _DCF_cls  # noqa: E402
from finverse.models.lbo import LBO as _LBO_cls  # noqa: E402
from finverse.models.three_statement import ThreeStatement as _ThreeStatement_cls  # noqa: E402
from finverse.models.comps import analyze as _comps_fn  # noqa: E402
from finverse.models.ddm import (  # noqa: E402
    gordon as _gordon_fn,
    h_model as _h_model_fn,
    multistage as _multistage_fn,
)
from finverse.models.sotp import Segment as _Segment_cls, analyze as _sotp_fn  # noqa: E402
from finverse.models.regime_dcf import analyze as _regime_dcf_fn  # noqa: E402
from finverse.models.synthetic_peers import build_peers as _synthetic_peers_fn  # noqa: E402

# Options & bonds
from finverse.options.black_scholes import price as _bs_price  # noqa: E402
from finverse.models.bonds import (  # noqa: E402
    price as _bond_price_fn,
    ytm_from_price as _ytm_from_price_fn,
)


# Public deprecated aliases (with deprecation behaviour)
DCF = _ClassAlias(_DCF_cls, "DCF", "finverse.models.dcf.DCF")
LBO = _ClassAlias(_LBO_cls, "LBO", "finverse.models.lbo.LBO")
ThreeStatement = _ClassAlias(
    _ThreeStatement_cls, "ThreeStatement", "finverse.models.three_statement.ThreeStatement"
)
Segment = _ClassAlias(_Segment_cls, "Segment", "finverse.models.sotp.Segment")

comps = _FunctionAlias(_comps_fn, "comps", "finverse.models.comps.analyze")
ddm_gordon = _FunctionAlias(_gordon_fn, "ddm_gordon", "finverse.models.ddm.gordon")
h_model = _FunctionAlias(_h_model_fn, "h_model", "finverse.models.ddm.h_model")
ddm_multistage = _FunctionAlias(
    _multistage_fn, "ddm_multistage", "finverse.models.ddm.multistage"
)
sotp = _FunctionAlias(_sotp_fn, "sotp", "finverse.models.sotp.analyze")
regime_dcf = _FunctionAlias(
    _regime_dcf_fn, "regime_dcf", "finverse.models.regime_dcf.analyze"
)
synthetic_peers = _FunctionAlias(
    _synthetic_peers_fn, "synthetic_peers", "finverse.models.synthetic_peers.build_peers"
)
bond_price = _FunctionAlias(_bond_price_fn, "bond_price", "finverse.models.bonds.price")
ytm_from_price = _FunctionAlias(
    _ytm_from_price_fn, "ytm_from_price", "finverse.models.bonds.ytm_from_price"
)


def option_call(*args: Any, **kwargs: Any) -> Any:
    """Deprecated.  Use `finverse.options.black_scholes.price(..., type=call)`."""
    _warn_legacy("option_call", "finverse.options.black_scholes.price (with type=call)")
    kwargs["type"] = "call"
    return _bs_price(*args, **kwargs)


def option_put(*args: Any, **kwargs: Any) -> Any:
    """Deprecated.  Use `finverse.options.black_scholes.price(..., type=put)`."""
    _warn_legacy("option_put", "finverse.options.black_scholes.price (with type=put)")
    kwargs["type"] = "put"
    return _bs_price(*args, **kwargs)


__all__ = [
    "DCF", "LBO", "ThreeStatement", "comps",
    "ddm_gordon", "h_model", "ddm_multistage",
    "sotp", "Segment", "regime_dcf", "synthetic_peers",
    "option_call", "option_put", "bond_price", "ytm_from_price",
]
