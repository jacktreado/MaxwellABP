# Configuration Reference

Every run is driven by a flat JSON object. Only `N` and `phi` are required;
everything else has a default. Fields and defaults below are taken verbatim from
[include/Config.hpp](../include/Config.hpp) and
[src/Config.cpp](../src/Config.cpp). The physical meaning of the dimensionless
inputs is on the [Model-Physics](Model-Physics#5-dimensionless-parameterization-what-the-json-exposes)
page.

A ready-to-edit default lives at [examples/input.json](../examples/input.json).

---

## Required

| Field | Type | Validation | Meaning |
|---|---|---|---|
| `N` | int | `> 0` | particle count |
| `phi` | double | in `(0, 1)` | 2D packing fraction (sets box size `L`) |

## Dimensionless control parameters

| Field | Type | Default | Validation | Sets |
|---|---|---|---|---|
| `Pe` | double | `1.0` | `≥ 0` | persistence time `tau_theta` |
| `De` | double | `1.0` | `≥ 0` | anchor spring stiffness `k_a` |
| `R` | double | `1.0` | `≥ 0` | anchor friction `gamma_a` |
| `C` | double | `0.001` | `≥ 0` | thermal energy `kT = C·epsilon` |
| `delta` | double | `1.0` | `> 0` | active force `f0` (via force balance) |
| `potential` | string | `"WCA"` | see below | pair potential type |

## Integrator & time evolution

| Field | Type | Default | Validation | Meaning |
|---|---|---|---|---|
| `integrator` | string | `"euler_maruyama"` | see below | integration method |
| `dt_init` | double | `0.001` | `> 0` | fixed Δt (EM/Heun) |
| `t_end` | double | `1.0` | `> 0` | total simulated time |
| `output_dt` | double | `0.01` | `> 0` | trajectory write interval (time-based) |

## Method-specific knobs

Shared by EM and Heun:

| Field | Type | Default | Validation | Meaning |
|---|---|---|---|---|
| `max_drift` | double | `0.1` | `≥ 0` (0 disables) | per-step deterministic drift cap (length units) |
| `r_skin` | double | `0.5` | `≥ 0` | Verlet skin; rebuild when drift `> r_skin/2` |

## I/O & initialization

| Field | Type | Default | Validation | Meaning |
|---|---|---|---|---|
| `output_file` | string | `"trajectory.h5"` | — | HDF5 output path (auto-set by `run.py`/`psweep.py`) |
| `init_mode` | string | `"lattice"` | `lattice` or `random` | initial configuration |
| `seed` | uint64 | `12345` | any | RNG seed |

## On-the-fly correlations (optional)

When `compute_correlations = true`, the other four become required and constrained.

| Field | Type | Default | Validation (if enabled) | Meaning |
|---|---|---|---|---|
| `compute_correlations` | bool | `false` | — | enable correlation sampling |
| `corr_dt_max` | double | `0.0` | `> 0`, `≤ t_end − t_warm` | maximum correlation lag |
| `n_corr_steps` | int | `0` | `> 0` | number of lag grid points |
| `t_warm` | double | `0.0` | `≥ 0` | warmup time before sampling begins |

## On-the-fly contact durations (optional)

| Field | Type | Default | Meaning |
|---|---|---|---|
| `compute_contact_durations` | bool | `false` | track per-pair contact lifetimes (cutoff = `sigma`) |

---

## Accepted string values

**`integrator`** (case/variant tolerant):

| Canonical | Accepted aliases |
|---|---|
| `euler_maruyama` | `EulerMaruyama`, `EM`, `em`, `euler-maruyama`, `eulermaruyama` |
| `heun` | `Heun`, `stochastic_heun`, `predictor_corrector`, `predictor-corrector` |

**`potential`:**

| Canonical | Accepted aliases | Cutoff |
|---|---|---|
| `WCA` | `wca` | `2^(1/6)·sigma ≈ 1.122` |
| `soft_sphere` | `softsphere`, `SoftSphere`, `soft-sphere` | `sigma` |

---

## Derived quantities (computed, not set)

`Config::recompute()` inverts the dimensionless inputs into the microscopic
parameters that actually enter the dynamics. These are **not** JSON fields — they
are computed and also written into the trajectory's root attributes.

| Derived | Formula |
|---|---|
| `epsilon` | `1.0` (frozen) |
| `kT` | `C · epsilon` |
| `L` | `sqrt(N·π·sigma² / (4·phi))` |
| `gamma` | `gamma_hat / (1 + R)` |
| `gamma_a` | `R · gamma` |
| `f0` | `f0ForOverlap(potential, delta)` — see [Model-Physics §6](Model-Physics#6-typical-pair-overlap--active-force) |
| `tau_theta` | `Pe · gamma_hat · sigma / f0` (or `0` if `f0 = 0` or `Pe ≤ 0`) |
| `k_a` | `gamma_a / (De · tau_theta)` (or `0` if `De ≤ 0` or `tau_theta = 0`) |

Frozen working units: `sigma = 1`, `epsilon = 1`, `gamma_hat = 1`.

> Run `./build/sim info <input.json>` to print all inputs **and** these derived
> values for a given config before running.

---

## Example configs

Minimal (everything else defaulted):

```json
{ "N": 64, "phi": 0.4 }
```

Active Brownian + soft sphere, Heun integrator, random init:

```json
{
  "N": 1000, "phi": 0.65,
  "Pe": 5.0, "De": 2.0, "R": 1.0, "C": 0.001, "delta": 0.9,
  "potential": "soft_sphere",
  "integrator": "heun",
  "dt_init": 0.001, "t_end": 100.0, "output_dt": 1.0,
  "init_mode": "random", "seed": 42
}
```

Heun with a small step for stiff contacts:

```json
{
  "N": 512, "phi": 0.5,
  "integrator": "heun",
  "dt_init": 0.001,
  "t_end": 50.0
}
```

Correlations enabled:

```json
{
  "N": 256, "phi": 0.5,
  "compute_correlations": true,
  "corr_dt_max": 5.0, "n_corr_steps": 100, "t_warm": 10.0,
  "t_end": 100.0, "output_dt": 0.5
}
```

See [Running](Running) for how to launch these and
[Output-and-Analysis](Output-and-Analysis) for what comes out.
