# MaxwellABP

A modular **C++17** engine for **2D active Brownian particles (ABPs)** with
**Maxwell-type viscoelastic anchors**, integrated under overdamped Langevin
(Brownian) dynamics. Each particle is repulsive (WCA or soft-sphere), optionally
self-propelled, and tethered to an anchor by a spring-in-series-with-a-dashpot — a
*Maxwell* viscoelastic element, which is where the name comes from. State is laid
out as a Structure-of-Arrays so the kernels port to GPU with minimal change.

> 📖 **Full documentation lives in the [wiki/](wiki/Home.md) folder** (and is meant
> to be published to this repo's GitHub Wiki).

---

## Features

- WCA / harmonic soft-sphere repulsion with periodic minimum-image.
- Active Brownian self-propulsion (`f0` from a steady-state overlap `delta`; persistence via `Pe`).
- Maxwell viscoelastic anchors (spring `k_a` + dashpot `gamma_a`, memory set by `De`, `R`).
- Two integrators: Euler–Maruyama and stochastic Heun (weak order 2).
- Sort-based cell / Verlet neighbor lists (GPU-shaped, with small-box brute-force fallback).
- On-the-fly velocity/force/orientation correlations and contact-duration statistics.
- Self-describing HDF5 trajectories + a Python loader and analysis pipeline.
- Optional ImGui + GLFW interactive viewer.

---

## Quick start

```bash
# Dependencies (macOS)
brew install hdf5 cmake

# Build the CLI + tests
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j

# Run one simulation, auto-organized under local/output/
./run.py --tag hello --t_end 0.1 --N 128 --phi 0.5
```

This writes `local/output/maxabp_run_hello/` containing the trajectory
(`maxabp_run_hello_seed0.h5`), the exact input config, the captured stdout, and a
`log.json` of run metadata.

Run the binary directly for full control:

```bash
./build/sim info examples/input.json          # show resolved + derived parameters
./build/sim run  examples/input.json --N 500 --phi 0.7 --integrator heun
```

---

## Documentation

| Page | Contents |
|---|---|
| [Model & Physics](wiki/Model-Physics.md) | potentials, Langevin SDEs, the Maxwell anchor, dimensionless `Pe / De / R / C / delta` |
| [Integrators](wiki/Integrators.md) | EM, Heun; cell-list neighbor search |
| [Building & Testing](wiki/Building.md) | dependencies, CMake, build options, test suite, troubleshooting |
| [Running](wiki/Running.md) | `sim` CLI, `run.py`, `psweep.py`, GUI |
| [Configuration Reference](wiki/Configuration-Reference.md) | every JSON field, default, and validation rule |
| [Output & Analysis](wiki/Output-and-Analysis.md) | HDF5 layout + Python tooling |

> **Publishing to the GitHub Wiki:** the `wiki/` pages are named for GitHub's wiki
> convention (`Home`, `_Sidebar`, etc.). Clone the wiki repo
> (`git clone <repo>.wiki.git`), copy the `wiki/*.md` files in, and push.

---

## Repository layout

```
MaxwellABP/
├── CMakeLists.txt           # build (sim + tests; GUI optional via -DBUILD_GUI=ON)
├── main.cpp                 # CLI: run / info / help
├── include/ , src/          # engine: System, Box, ForceCalculator, CellList,
│                            #   integrators, Config, TrajectoryWriter, accumulators
├── test/                    # GoogleTest suite (~129 tests)
├── gui/                     # ImGui + GLFW viewer (optional)
├── examples/input.json      # default base config
├── run.py                   # single local run  -> local/output/
├── psweep.py                # parameter sweeps   -> SLURM jobs
├── python/                  # bdtrajectory loader + analysis pipeline
├── tests/                   # pytest suite for the Python pipeline
└── wiki/                    # documentation
```

---

## Testing

```bash
ctest --test-dir build --output-on-failure
```

See [Building & Testing](wiki/Building.md) for details and per-suite filters.
