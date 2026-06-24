# Running Simulations

There are three ways to run, from lowest to highest level:

1. **`sim`** — the C++ binary directly (one config, full control).
2. **`run.py`** — a single local run, auto-organized under `local/output/`.
3. **`psweep.py`** — parameter sweeps that generate (and optionally submit) SLURM jobs.

All three read the same JSON config; see
[Configuration-Reference](Configuration-Reference) for every field.

---

## 1. The `sim` binary

```
sim run   <input.json> [--key value ...]    Run a simulation.
sim info  <input.json> [--key value ...]    Parse + print the resolved config (no run).
sim help                                    Usage.
```

`sim info` is the quickest way to see how your dimensionless inputs map to
microscopic parameters (`f0`, `tau_theta`, `k_a`, `L`, …) before committing to a run.

### CLI overrides

Any allowlisted JSON field can be overridden on the command line, in either form:

```bash
./build/sim run examples/input.json --phi 0.7 --N 500 --Pe 8
./build/sim run examples/input.json --phi=0.7 --potential=soft_sphere --compute_correlations=true
```

Overrides are type-inferred (numbers, bools) and merged onto the file **before**
validation and the derived-quantity recompute, so they go through exactly the same
checks. Unknown flags error out. The trajectory is written to the config's
`output_file` (default `trajectory.h5`).

---

## 2. `run.py` — single local run (recommended)

[run.py](../run.py) builds `sim` (unless `--no-build`), materializes one input JSON
from a base config plus overrides, runs the simulation locally, and collects
everything under a per-tag directory.

```bash
# Smoke test: short run, small system
./run.py --tag smoke --t_end 0.05 --N 64 --phi 0.4

# Active Brownian + soft sphere, a specific seed, reuse the existing binary
./run.py --tag abp --Pe 20 --delta 0.9 --potential soft_sphere --seed 7 --no-build

# Resolve + print the merged config without running (or writing) anything
./run.py --tag smoke --list-only
```

### Output layout

```
local/output/maxabp_run_<tag>/
  maxabp_run_<tag>_seed<seed>.h5      # trajectory (HDF5)
  maxabp_run_<tag>_seed<seed>.json    # the exact input config used
  maxabp_run_<tag>_seed<seed>.out     # captured sim stdout/stderr
  log.json                            # run metadata (see below)
```

`log.json` records the tag, timestamp, full command, base-config path, binary path,
the `overrides` applied, the complete `resolved_config`, the seed, all output
paths, the `return_code`, `wall_time_sec`, and a `success` flag — enough to
reproduce or audit the run later.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--tag` | *(required)* | run identifier → `maxabp_run_<tag>/` |
| `--seed` | `0` | RNG seed; appears in the output filenames |
| `--base` | `examples/input.json` | base config to start from |
| `--out-dir` | `local/output` | root output directory |
| `--no-build` | off | skip the cmake/make step (use the existing binary) |
| `--build-type` | `Release` | `CMAKE_BUILD_TYPE` for the auto-build |
| `--list-only` | off | print the resolved config and exit; write nothing |
| `--<key> value` | — | override any allowlisted Config field |

`seed` and `output_file` are owned by `run.py`: use `--seed` for the former, and
the output path is always auto-named — passing them as `--key` overrides is
rejected with a hint.

---

## 3. `psweep.py` — parameter sweeps + SLURM

[psweep.py](../psweep.py) builds the Cartesian product of one or more **physical**
sweep variables (`N, phi, delta, Pe, De, R, C`) across a range of seeds, writes one
input JSON per (combination, seed), and emits a SLURM array job per combination.
Numerical/I-O knobs (integrator, tolerances, `t_end`, …) are set once as constants,
not swept.

```bash
# List the eligible sweep variables and the --ljson schema
./psweep.py --info

# 1-D sweep over phi (5 points), 10 seeds each — generate files, don't submit
./psweep.py --psweep --tag phi_dense --note "phi sweep" \
    --loop --var phi --start 0.1 --stop 0.5 --num 5 --format lin \
    --start-seed 0 --num-seeds 10

# 2-D sweep (phi × Pe) from a JSON spec, submitted to SLURM
./psweep.py --psweep --tag big --note "phi x Pe" --ljson sweep.json \
    --start-seed 0 --num-seeds 8 \
    --submit --partition short --time 02:00:00 --mem 2G

# Hold numerical knobs constant across the whole sweep
./psweep.py --psweep --tag heun --note "heun all" \
    --loop --var Pe --start 1 --stop 100 --num 4 --format log \
    --integrator heun --t_end 50 --output_dt 0.5 \
    --start-seed 0 --num-seeds 4
```

Each sweep lands in `psweep_<date>_<tag>/` with per-combination run directories,
`psweep_map.json` (index → parameter values), and `log.json` (full sweep metadata).
Use `--list-only` for a dry run and `--submit` (with `--partition`) to actually
`sbatch`. By default `psweep.py` rebuilds `sim` first; pass `--no-build` to skip.

> **`run.py` vs `psweep.py`:** `run.py` *executes* one run locally and waits;
> `psweep.py` *generates* (and optionally submits) many runs for a cluster. They
> share the same base config ([examples/input.json](../examples/input.json)) and the
> same override-parsing code.

---

## 4. The interactive GUI

If built with `-DBUILD_GUI=ON` (see [Building](Building)):

```bash
./build/gui/sim_gui
```

The viewer runs the simulation in memory (no trajectory file) and exposes
$\delta$, the friction ratio, and the relaxation-time ratio as sliders, with `N`,
`phi`, `kT`, `dt`, and the potential type as live controls.

---

After a run, load the `.h5` with the Python tools — see
**[Output-and-Analysis](Output-and-Analysis)**.
