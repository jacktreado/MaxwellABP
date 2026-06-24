# Integrators & Neighbor Lists

MaxwellABP discretizes the overdamped Langevin system (see
[Model-Physics](Model-Physics#3-equations-of-motion)) with one of two
fixed-step stochastic integrators. The `integrator` JSON field selects between them.

| `integrator` value | Method | Order (additive noise) | Force evals / step | Tuning knobs |
|---|---|---|---|---|
| `euler_maruyama` (default) | Euler–Maruyama | weak/strong 1 | 1 | `dt_init`, `max_drift`, `r_skin` |
| `heun` | stochastic Heun (predictor–corrector) | weak 2, strong 1 | 2 | `dt_init`, `max_drift`, `r_skin` |

Both integrate the **same** physics: pair force + active drive + anchor
spring + thermal/rotational noise.

---

## Euler–Maruyama

Fixed-step, cheapest, one force evaluation per step
([include/Integrator.hpp](../include/Integrator.hpp)). The update at step `dt`:

$$\mathbf{r}_i \mathrel{+}= \mu\big[\mathbf{F}_i^\text{pair} + f_0\hat{\mathbf{e}}_i - k_a(\mathbf{r}_i-\mathbf{a}_i)\big]\,\Delta t + \sqrt{\tfrac{2k_BT}{\gamma}\Delta t}\,\boldsymbol{\xi}_i,$$
$$\theta_i \mathrel{+}= \sqrt{2D_r\,\Delta t}\,\xi_i^\theta, \qquad \mathbf{a}_i \mathrel{+}= \tfrac{1}{\gamma_a}k_a(\mathbf{r}_i-\mathbf{a}_i)\Delta t + \sqrt{\tfrac{2k_BT}{\gamma_a}\Delta t}\,\boldsymbol{\xi}_i^a .$$

**Drift cap (`max_drift`):** the deterministic displacement (pair + active +
spring) is clamped to `max_drift` length units *before* the noise is added. This
prevents blow-up under stiff WCA contacts or high mobility. The noise is **not**
rescaled, so equilibrium statistics are preserved. Set `max_drift = 0` to disable.

Use EM for a robust baseline, debugging, or when `dt_init` is already small.

---

## Stochastic Heun (predictor–corrector)

Two-stage, weak order 2 for additive noise
([include/HeunIntegrator.hpp](../include/HeunIntegrator.hpp)). Both stages reuse the
**same** noise sample $Z$:

$$\text{predict: } \tilde{\mathbf{r}} = \mathbf{r}_n + \mathbf{b}(\mathbf{r}_n)\Delta t + \sigma_r\sqrt{\Delta t}\,Z,$$
$$\text{correct: } \mathbf{r}_{n+1} = \mathbf{r}_n + \tfrac{1}{2}\big[\mathbf{b}(\mathbf{r}_n) + \mathbf{b}(\tilde{\mathbf{r}})\big]\Delta t + \sigma_r\sqrt{\Delta t}\,Z.$$

The averaged drift is second-order accurate, which typically allows **3–5× larger
`dt_init`** at matched mean-observable error. Net speedup over EM is usually
1.5–2.5× despite the doubled force cost. The drift cap is applied independently to
predictor and corrector, so the averaged step stays bounded. The cell list is
**not** rebuilt between the two stages (the predictor displacement is well under
`r_skin/2`).

Use Heun as the default production workhorse when you want accuracy per wall-clock.

> `kT = 0` turns off translational + anchor noise; `D_r = 0` freezes orientations;
> `gamma_a = 0` freezes anchors. These fall out of the dimensionless inputs (see
> [Model-Physics §5](Model-Physics#degenerate-limits-handled-automatically)).

---

## Cell lists & Verlet neighbor lists {#cell-lists}

To avoid the $O(N^2)$ pair loop, forces use a **sort-based cell list with a Verlet
skin** ([include/CellList.hpp](../include/CellList.hpp)). The build pipeline is four
independent stages (each a future CUDA kernel):

1. **computeCellIds** — `cell_id[i] = cx + nx*cy`.
2. **sortByCellId** — co-sort `(cell_id, particle_id)`.
3. **findCellBoundaries** — derive `cell_start[c]`, `cell_end[c]`.
4. **buildVerletList** — count → exclusive prefix-sum → fill a CSR neighbor list, walking the 3×3 periodic stencil.

**Search radius / rebuild:** neighbors are gathered within
$r_\text{verlet} = r_\text{cut} + r_\text{skin}$. The list is rebuilt only when some
particle has drifted more than $r_\text{skin}/2$ since the last build (a PBC-aware
$O(N)$ check). Larger `r_skin` ⇒ fewer rebuilds but more neighbors per particle.

**Small-box fallback:** when $\min(L_x, L_y) < 3(r_\text{cut} + r_\text{skin})$ the
3×3 stencil would double-count through the periodic wrap, so the code silently
falls back to brute force. With default `r_skin = 0.5` and WCA this triggers below
roughly $L \approx 4.9\,\sigma$ (small `N` and/or high `phi`); you'll see a
"box too small for cell list" note in the run log. It is correct, just $O(N^2)$.

---

## Choosing an integrator

- **Just want correct results, simply:** `euler_maruyama` with a small `dt_init`.
- **Best accuracy per wall-clock (most production runs):** `heun`.
- **Stiff deterministic forces (small `delta`, hard contacts):** `heun` with a smaller `dt_init`.

Validate any choice by halving `dt_init` and confirming your
observables are unchanged. See [Running](Running) for invocation and
[Output-and-Analysis](Output-and-Analysis) for the diagnostics to check.
