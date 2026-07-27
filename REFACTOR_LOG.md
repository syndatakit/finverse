# finverse refactor log

## Phase 1 — Baseline (pre-refactor)

- **Repo state**: `syndatakit/finverse` fork, upstream `Nityahapani/finverse`. v0.8.0 in pyproject, v0.7.0 in `__init__.py` (mismatch).
- **File count**: 87 .py files across 15 subpackages.
- **Syntax**: 0 errors across all 87 files.
- **Top-level imports**: `__init__.py` re-exports `DCF, LBO, comps, option_call, option_put, bond_price, ytm_from_price, ...` as flat names AND imports `options, derivatives` subpackages — duplicate public surface.
- **Dupe domains**:
  - Options: canonical at `finverse.options.black_scholes.price` (new, complete), legacy at `finverse.models.options.call/put` (old, also complete).
  - Bonds: only at `finverse.models.bonds` (no `finverse.bonds` package).
- **`_` prefix on module files** (misleading — doesn't make modules private in Python):
  - `finverse/ml/_ensemble_weights.py`, `_factor_regime_model.py`, `_revision_tracker.py`, `_surprise_model.py`
  - `finverse/risk/_scenarios.py`, `_stress_engine.py`
  - `finverse/derivatives/_blacks_model.py`, `_discount.py`
- **Import test** (without deps): fails on `rich` (not installed in sandbox). Confirms `finverse.utils.display` is the leaf blocker for `import finverse` to succeed.
- **Test set**: 8 test files (`test_dcf.py`, `test_forecast.py`, `test_phase4.py`, `test_phase5.py`, `test_phase6.py`, `test_sensitivity.py`, `test_v07_modules.py`).

## Decisions

- **Deprecation strategy: option (a)** — keep flat names as aliases with `DeprecationWarning`, no breaking change.
- **Canonical paths**:
  - `finverse.options.black_scholes.price` (and parent `finverse.options.price` as convenience re-export)
  - `finverse.models.bonds.price` (no dupe exists; just keep + deprecate flat `bond_price`)
  - DCF/LBO/etc. stay where they are, just re-exported via the compat shim.
- **`_` prefix files**: rename to honest names. `_` on a module name is a misleading convention (Python doesn't enforce it for modules).

## Phase 2 — Changes applied (in workspace; for review via patch file)

### Version fix
- `finverse/__init__.py` `__version__`: `0.7.0` → `0.8.0`
- `finverse/__init__.py` docstring header: updated to `v0.8.0`
- `pyproject.toml` already at `0.8.0` — no change

### New: `finverse/_compat.py` (deprecation shim)
- `DCF, LBO, ThreeStatement, Segment` → `_ClassAlias` (deprecation fires on construction)
- `comps, ddm_gordon, h_model, ddm_multistage, sotp, regime_dcf, synthetic_peers, bond_price, ytm_from_price` → `_FunctionAlias` (deprecation fires on call)
- `option_call, option_put` → plain functions that emit warning + delegate to `finverse.options.black_scholes.price` with `type='call'/'put'`
- Warning message includes the legacy name, the canonical replacement, and the removal version (v1.0.0)
- Imports do NOT fire (matches numpy/pandas convention)
- Attribute access on class aliases does NOT fire
- `isinstance` against the alias works for instances of the underlying class
- TypeError protection: `option_call(..., type="put")` no longer raises — the deprecation default wins

### Updated: `finverse/__init__.py`
- Re-exports flat names from `finverse._compat` so `from finverse import DCF` continues to work
- `__all__` lists both subpackage handles and the deprecated flat names
- New docstring header

### Renames (8 files)
| Old                                  | New                                       |
| ------------------------------------ | ----------------------------------------- |
| `finverse/ml/_ensemble_weights.py`   | `finverse/ml/ensemble_weights.py`         |
| `finverse/ml/_factor_regime_model.py`| `finverse/ml/factor_regime_model.py`      |
| `finverse/ml/_revision_tracker.py`   | `finverse/ml/revision_tracker.py`         |
| `finverse/ml/_surprise_model.py`     | `finverse/ml/surprise_model.py`           |
| `finverse/risk/_scenarios.py`        | `finverse/risk/scenarios_internal.py`     |
| `finverse/risk/_stress_engine.py`    | `finverse/risk/stress_engine.py`          |
| `finverse/derivatives/_blacks_model.py` | `finverse/derivatives/blacks_model.py`  |
| `finverse/derivatives/_discount.py`  | `finverse/derivatives/discount.py`        |

### Import updates (7 files, sed pass)
- `finverse/derivatives/rates.py`
- `finverse/ml/earnings_surprise.py`
- `finverse/ml/macro_factor_rotation.py`
- `finverse/ml/price_target_ensemble.py`
- `finverse/risk/stress_engine.py`
- `finverse/risk/stress_testing.py`
- `tests/test_v07_modules.py` (16 import lines)

### New: `MIGRATION.md`
- Full migration map (legacy → canonical)
- Examples for options re-routing
- Renames documented
- Timeline: deprecation on 0.8.0, removal at 1.0.0

## Phase 3 — Verification

- **Syntax check**: 0 errors across 97 .py files (87 original + `_compat.py` + 8 renames + 1 `__init__` rewrite)
- **Deprecation shim test suite**: 10/10 tests pass
  - imports don't fire
  - attribute access on class aliases doesn't fire
  - class construction fires
  - function call fires
  - option_call routes to BS with `type='call'`
  - option_put routes to BS with `type='put'`
  - option_call override of user `type=` is safe (deprecation wins)
  - isinstance against the alias works
  - bond_price fires
  - ytm_from_price fires
- **No remaining `_` references** to the renamed modules anywhere in `finverse/`, `tests/`, `examples/`

## Why the code changes are NOT in this PR

The workspace produced a single 184KB patch file (`finverse-refactor-v0.8.0.patch`)
that contains all the code changes described above.  This branch deliberately
contains only the **documentation** for the refactor.  Reasons:

1. The fork's local clone has no commit history, so the pre-refactor contents
   of the `_prefixed` modules are not recoverable from the local filesystem.
   Pushing 16 file changes from the local clone risks silent corruption.
2. The patch file is a single reviewable artifact.  The reviewer can run
   `git apply` and inspect the diff before any of it lands on main.
3. This PR can be merged independently of the code changes.  Once the
   patch is approved, a follow-up PR can land the code.

## Out of scope (follow-up PRs)

- `pull/` package refactor (yfinance coupling)
- `ml/` 17-file package internal consolidation
- README rewrite (1114 lines, scope separate)
- Dependency trimming (xgboost + scikit-learn in core deps)
- Adding `mypy --strict` or `ruff` to CI
- Test file rename (phase4/5/6 → domain-based)
- Re-organization of `finverse/models/` (mixes valuation models with macro/options/bonds)

## How to apply the patch (for the reviewer)

```bash
# In the repo root
git apply --3way finverse-refactor-v0.8.0.patch

# Then remove the old _-prefixed files (renames):
cd finverse
git rm derivatives/_blacks_model.py derivatives/_discount.py
git rm ml/_ensemble_weights.py ml/_factor_regime_model.py ml/_revision_tracker.py ml/_surprise_model.py
git rm risk/_scenarios.py risk/_stress_engine.py
git add .
git commit -m "refactor: v0.8.0 cleanup (deprecation shim + module renames)"

# Install (in your venv)
pip install -e ".[dev]"

# Run all tests
pytest

# Filter out the deprecation warnings if they're noisy in test output
pytest -W "ignore::DeprecationWarning:finverse"

# Confirm deprecation warnings are firing
python -W "default::DeprecationWarning" -c "from finverse import DCF, option_call, comps; DCF(); option_call(100, 100, 1); comps('AAPL')"
```
