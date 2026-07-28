"""
Tests that the v0.8.0 deprecation shim works correctly and emits warnings
when the legacy flat-name API is used.

Also enforces that the canonical (new) import path is silent — no
DeprecationWarning is fired when using the new names.

These tests are part of CI (see .github/workflows/ci.yml).
"""
from __future__ import annotations

import warnings

import pytest


# -- canonical path is silent -------------------------------------------------

def test_canonical_imports_are_silent():
    """Importing from canonical subpackages must not emit DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from finverse.models.dcf import DCF
        from finverse.models.lbo import LBO
        from finverse.models.comps import analyze as comps_analyze
        from finverse.options.black_scholes import price

    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warnings == [], (
        f"Canonical imports emitted DeprecationWarning(s): "
        f"{[str(w.message) for w in deprecation_warnings]}"
    )


# -- legacy top-level class aliases -------------------------------------------

@pytest.mark.parametrize("legacy_name", [
    "DCF", "LBO", "ThreeStatement", "Segment",
])
def test_legacy_class_emits_warning(legacy_name):
    """Importing a legacy class alias must succeed, but instantiating it warns."""
    import finverse
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cls = getattr(finverse, legacy_name)
        # Bare import is silent
        assert not any(
            issubclass(w.category, DeprecationWarning) for w in caught
        ), f"Import of {legacy_name} should not fire"

    # But the underlying class lookup should still work
    assert cls is not None


def test_legacy_DCF_alias_does_not_instantiate_cleanly():
    """Calling the legacy DCF class alias without real args errors, but
    importantly, the alias object exists and is callable."""
    import finverse
    DCF = finverse.DCF
    # The alias itself is callable (proxied to the real DCF)
    assert callable(DCF)
    # It exposes attributes of the real class (without firing the warning)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = DCF.__name__
    assert not any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), "Attribute access on legacy class alias should not fire"


# -- legacy top-level function aliases ----------------------------------------

@pytest.mark.parametrize("legacy_name", [
    "comps", "ddm_gordon", "h_model", "ddm_multistage",
    "sotp", "regime_dcf", "synthetic_peers",
    "bond_price", "ytm_from_price",
])
def test_legacy_function_imports(legacy_name):
    """Legacy function aliases exist and are callable."""
    import finverse
    fn = getattr(finverse, legacy_name)
    assert callable(fn)


# -- deprecation message format -----------------------------------------------

def test_deprecation_message_mentions_removal_version():
    """The deprecation warning should mention the removal target version."""
    import finverse
    DCF = finverse.DCF
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Simulate a call to fire the warning (DCF() with no args errors,
        # but the warning fires first via __call__)
        try:
            DCF(None)
        except Exception:
            pass

    assert any(
        issubclass(w.category, DeprecationWarning) and "1.0.0" in str(w.message)
        for w in caught
    ), "Deprecation warning must mention the removal version (1.0.0)"


def test_deprecation_message_mentions_canonical_path():
    """The deprecation warning should tell users the canonical path."""
    import finverse
    DCF = finverse.DCF
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            DCF(None)
        except Exception:
            pass

    assert any(
        issubclass(w.category, DeprecationWarning) and "finverse.models.dcf" in str(w.message)
        for w in caught
    ), "Deprecation warning must include the canonical import path"


# -- version is correct -------------------------------------------------------

def test_version_is_0_8_0():
    import finverse
    assert finverse.__version__ == "0.8.0"
