# Output Format & Analysis

Each run writes a single **HDF5** trajectory file
([include/TrajectoryWriter.hpp](../include/TrajectoryWriter.hpp)). The `python/`
package provides a loader and a reduction pipeline for analyzing one file or a whole
sweep.

---

## HDF5 file layout

```
/                                  root group
  attrs: full resolved Config — N, phi, Pe, De, R, C, delta, potential,
         sigma, epsilon, gamma, L, kT, f0, tau_theta, gamma_a, k_a,
         dt_init, t_end, output_dt,
         output_file, init_mode, seed

/frame_00000000                    one group per output frame
  attrs: step (uint64), time (double), frame (uint64), Lx (double), Ly (double)
  positions     (N, 2) float64     [x_i, y_i]
  velocities    (N, 2) float64     [vx_i, vy_i]
  orientations  (N,)   float64     theta_i  (radians)
  anchors       (N, 2) float64     [ax_i, ay_i]
  forces        (N, 2) float64     net PAIR force on each particle
/frame_00000001
  ...
```

Frames are written every `output_dt` of simulated time (the last step before each
boundary is shortened so frames land exactly on multiples of `output_dt`).

> **Forces caveat:** the `forces` dataset holds **only** the pair-interaction force
> (`System::fx_/fy_` from `ForceCalculator::compute`). The active drive and anchor
> spring contributions live inside the integrator step and are **not** included.

### Optional groups

Written only when the corresponding feature is enabled in the config:

```
/correlations                      (compute_correlations = true)
  attrs: corr_dt, corr_dt_max, n_corr_steps, t_warm, n_samples
  tau    (n_corr_steps,) float64   lag grid tau_k = k·corr_dt
  C_vn   (n_corr_steps,) float64   <v(t) · n_hat(t − tau_k)>
  C_Fn   (n_corr_steps,) float64   <F(t) · n_hat(t − tau_k)>
  C_vv   (n_corr_steps,) float64   <v(t) · v(t − tau_k)>
  count  (n_corr_steps,) uint64    contributions per lag

/contact_durations                 (compute_contact_durations = true)
  attrs: contact_cutoff, count, mean, stddev, min, max,
         in_progress, in_progress_sum_duration, n_samples
```

`C_vn`, `C_Fn`, `C_vv` are ensemble + time averages over particles and sample
times ([include/CorrelationAccumulator.hpp](../include/CorrelationAccumulator.hpp));
contact statistics use a streaming Welford accumulator over *completed* contacts,
reporting still-open ones separately so you can gauge censoring bias
([include/ContactDurationAccumulator.hpp](../include/ContactDurationAccumulator.hpp)).

---

## Loading a trajectory in Python

[python/bdtrajectory.py](../python/bdtrajectory.py) wraps a file with a Pythonic API:

```python
import sys; sys.path.insert(0, "python")
from bdtrajectory import BDTrajectory

traj = BDTrajectory("local/output/maxabp_run_smoke/maxabp_run_smoke_seed0.h5")

len(traj)                 # number of frames
traj._params["N"]         # any root Config attribute
traj.positions(0)         # (N, 2) at frame 0
traj.velocities(-1)       # (N, 2) at the last frame (or None for older files)
traj.orientations(0)      # (N,) or None
traj.forces(0)            # (N, 2) pair forces, or None
traj.time(5)              # simulated time at frame 5
traj.frame_box(0)         # (Lx, Ly)

# Built-in derived observables
traj.mean_squared_displacement(reference_frame=0)
traj.mean_speed()
traj.max_cluster_fraction()

# Visualization helpers
traj.plot_frame(0)
traj.animate()
```

It supports iteration (`for fr in traj:`), indexing (`traj[i]` → positions), and use
as a context manager.

---

## Analysis pipeline (sweeps)

[python/analysis/](../python/analysis) reduces per-frame data into ensemble
observables and aggregates across seeds. Analyses are registered by name; the
built-ins are:

| Name | What it computes | Needs |
|---|---|---|
| `msd` | mean squared displacement vs. lag time | `positions` |
| `hexatic` | hexatic order parameter ψ₆ (PBC Delaunay) | `positions` |
| `clusters` | connected-component / cluster-size statistics (PBC) | `positions` |
| `force_orientation` | F·n̂ alignment + its time cross-correlation | `forces`, `orientations` |
| `correlations` | ensemble average of the on-the-fly C++ correlator | `/correlations` group |
| `contact_duration` | contact-lifetime statistics | `/contact_durations` group |

These operate over the directory structure that `psweep.py` produces (see
[Running](Running#3-psweeppy--parameter-sweeps--slurm)). The Python test suite under
[tests/](../tests) (`pytest`) exercises the pipeline end-to-end; the demo notebook
[python/demo.ipynb](../python/demo.ipynb) walks through loading and plotting.

---

## Quick inspection without Python

If you have the HDF5 tools installed:

```bash
h5ls  local/output/maxabp_run_smoke/maxabp_run_smoke_seed0.h5          # top-level groups
h5dump -a / local/output/.../maxabp_run_smoke_seed0.h5                 # root Config attrs
h5ls -r local/output/.../maxabp_run_smoke_seed0.h5 | head              # recursive listing
```

---

See **[Model-Physics](Model-Physics)** for what the observables mean and
**[Configuration-Reference](Configuration-Reference)** for enabling the optional
correlation / contact-duration outputs.
