# Migration guide — finverse 0.7.x → 0.8.x

This release refactors the top-level public surface to use subpackage paths as
the canonical API.  **No imports are broken**: every legacy flat-name import
continues to work, but emits `DeprecationWarning` and will be removed in
**1.0.0**.

If your code uses `warnings.filterwarnings("error", ...)` in tests, expect
new warnings.  Either ignore the `DeprecationWarning` category or migrate
to the canonical paths.

## Migration map

### Valuation models (canonical: `finverse.models.*`)

| Legacy (deprecated)                       | Canonical (new)                                                |
| ----------------------------------------- | -------------------------------------------------------------- |
| `from finverse import DCF`                | `from finverse.models.dcf import DCF`                          |
| `from finverse import LBO`                | `from finverse.models.lbo import LBO`                          |
| `from finverse import ThreeStatement`     | `from finverse.models.three_statement import ThreeStatement`   |
| `from finverse import comps`              | `from finverse.models.comps import analyze`                    |
| `from finverse import ddm_gordon`         | `from finverse.models.ddm import gordon`                       |
| `from finverse import h_model`            | `from finverse.models.ddm import h_model`                      |
| `from finverse import ddm_multistage`     | `from finverse.models.ddm import multistage`                   |
| `from finverse import sotp`               | `from finverse.models.sotp import analyze`                     |
| `from finverse import Segment`            | `from finverse.models.sotp import Segment`                     |
| `from finverse import regime_dcf`         | `from finverse.models.regime_dcf import analyze`               |
| `from finverse import synthetic_peers`    | `from finverse.models.synthetic_peers import build_peers`     |

### Options

| Legacy (deprecated)                       | Canonical (new)                                                |
| ----------------------------------------- | -------------------------------------------------------------- |
| `from finverse import option_call`        | `from finverse.options.black_scholes import price` (then pass `type='call'`) |
| `from finverse import option_put`         | `from finverse.options.black_scholes import price` (then pass `type='put'`)  |

**Example:**

```python
# Old (deprecated)
from finverse import option_call, option_put
c = option_call(S=185, K=190, T=0.25, r=0.053, sigma=0.28)
p = option_put(S=185, K=190, T=0.25, r=0.053, sigma=0.28)

# New (canonical)
from finverse.options.black_scholes import price
c = price(S=185, K=190, T=0.25, r=0.053, sigma=0.28, type="call")
p = price(S=185, K=190, T=0.25, r=0.053, sigma=0.28, type="put")
```

Or via the parent subpackage convenience re-export:

```python
from finverse import options
c = options.price(S=185, K=190, T=0.25, r=0.053, sigma=0.28, type="call")
```

### Bonds

| Legacy (deprecated)                       | Canonical (new)                                                |
| ----------------------------------------- | -------------------------------------------------------------- |
| `from finverse import bond_price`         | `from finverse.models.bonds import price`                      |
| `from finverse import ytm_from_price`     | `from finverse.models.bonds import ytm_from_price`             |

## Renames (no API change, internal only)

The following module files were renamed to drop the leading underscore — the
underscore convention does not make modules private in Python:

- `finverse.ml._ensemble_weights` → `finverse.ml.ensemble_weights`
- `finverse.ml._factor_regime_model` → `finverse.ml.factor_regime_model`
- `finverse.ml._revision_tracker` → `finverse.ml.revision_tracker`
- `finverse.ml._surprise_model` → `finverse.ml.surprise_model`
- `finverse.risk._scenarios` → `finverse.risk.scenarios_internal`
- `finverse.risk._stress_engine` → `finverse.risk.stress_engine`
- `finverse.derivatives._blacks_model` → `finverse.derivatives.blacks_model`
- `finverse.derivatives._discount` → `finverse.derivatives.discount`

If you imported any of these directly (e.g.
`from finverse.ml._ensemble_weights import ...`), update the import.  These
were never part of the documented public surface.

## Timeline

- **0.8.0** (this release): deprecation warnings on, no removal.
- **0.9.0**: same; no functional changes.
- **1.0.0**: deprecated aliases removed.  Pin to `>=0.8,<1.0` if you cannot
  migrate by 1.0.
