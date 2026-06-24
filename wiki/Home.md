# MaxwellABP Wiki

**MaxwellABP** is a modular C++17 engine for **2D active Brownian particles** with
**Maxwell-type viscoelastic anchors**, integrated under overdamped Langevin
(Brownian) dynamics.

The name comes from the model: each particle is tethered to an anchor by a **spring
in series with a dashpot** — a *Maxwell* viscoelastic element — while being driven
as an **A**ctive **B**rownian **P**article.

---

## Start here

| Page | What's in it |
|---|---|
| [Model-Physics](Model-Physics) | potentials, the Langevin SDEs, the Maxwell anchor, and the dimensionless `Pe / De / R / C / delta` parameterization |
| [Integrators](Integrators) | Euler–Maruyama, stochastic Heun, and the cell-list neighbor search |
| [Building](Building) | dependencies, CMake configure/build, options, and the test suite |
| [Running](Running) | the `sim` CLI, `run.py` (single local run), `psweep.py` (sweeps), and the GUI |
| [Configuration-Reference](Configuration-Reference) | every JSON field, default, and validation rule |
| [Output-and-Analysis](Output-and-Analysis) | the HDF5 layout and the Python loader + analysis pipeline |

---

## Features

- **Repulsive pair interactions:** WCA or harmonic soft-sphere, with PBC minimum-image.
- **Active Brownian self-propulsion:** force `f0` set from a steady-state overlap `delta`; orientational persistence via `Pe`.
- **Maxwell viscoelastic anchors:** tunable spring `k_a` + dashpot `gamma_a` (memory set by `De`, `R`).
- **Multiple integrators:** Euler–Maruyama and stochastic Heun (weak order 2).
- **Cell / Verlet neighbor lists:** sort-based, with a four-stage GPU-shaped pipeline and brute-force fallback for small boxes.
- **On-the-fly observables:** velocity/force/orientation correlations and contact-duration statistics, computed during the run.
- **HDF5 trajectories:** self-describing files (full config in the root attributes) with a Python analysis package.
- **Optional GUI:** an ImGui + GLFW interactive viewer (`-DBUILD_GUI=ON`).

---

## 60-second quick start

```bash
# 1. Dependencies (macOS)
brew install hdf5 cmake

# 2. Build the CLI + tests
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j

# 3. Run one simulation, organized under local/output/
./run.py --tag hello --t_end 0.1 --N 128 --phi 0.5

# 4. Inspect it
python3 -c "import sys; sys.path.insert(0,'python'); \
from bdtrajectory import BDTrajectory as T; \
t=T('local/output/maxabp_run_hello/maxabp_run_hello_seed0.h5'); \
print('frames:', len(t), 'N:', t._params['N'])"
```

See [Running](Running) for `sim`, `run.py`, and `psweep.py` in depth.

---

## Repository layout

```
MaxwellABP/
├── CMakeLists.txt           # build (sim + tests; GUI optional)
├── main.cpp                 # CLI: run / info / help
├── include/ , src/          # engine: System, Box, ForceCalculator, CellList,
│                            #   integrators, Config, TrajectoryWriter, accumulators
├── test/                    # GoogleTest suite (~129 tests)
├── gui/                     # ImGui + GLFW viewer (optional)
├── examples/input.json      # default base config
├── run.py                   # single local run  -> local/output/
├── psweep.py                # parameter sweeps   -> SLURM
├── python/                  # bdtrajectory loader + analysis pipeline
├── tests/                   # pytest suite for the Python pipeline
└── wiki/                    # this documentation
```

---

## Roadmap

Done:

- [x] HDF5 (`.h5`) trajectory output
- [x] Python visualization / analysis classes
- [x] Activity (active Brownian)
- [x] Viscoelasticity (Maxwell anchors)
- [x] Soft-sphere `delta` handling fixed in the GUI

In progress / planned:

- [ ] **GPU port** — figure out testing strategy (multi-threaded, or many parameter sets at once)
- [ ] Higher-order BD integrators (Stratonovich correctors, etc.)
- [ ] Hexagonal lattice initializer for `phi > π/4`
- [ ] More observables in their own decoupled module (RDF, virial pressure)
- [ ] Multi-GPU / MPI domain decomposition (SoA layout already anticipates it)
