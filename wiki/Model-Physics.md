# Model & Physics

MaxwellABP simulates **2D active Brownian particles (ABPs)** that interact through
a purely repulsive pair potential and are each tethered to a **Maxwell
viscoelastic anchor** (a spring in series with a dashpot). The dynamics are
overdamped Langevin (Brownian) — there is no momentum, only balance of forces.

This page collects the continuum model, the microscopic equations of motion, and
the **dimensionless parameterization** that the input JSON actually exposes.

---

## 1. Working units

Three scales are frozen to `1`, which fixes the unit system:

| Quantity | Symbol | Value | Meaning |
|---|---|---|---|
| Length | $\sigma$ | 1 | particle diameter |
| Energy | $\varepsilon$ | 1 | pair-interaction scale |
| Friction | $\hat{\gamma}$ | 1 | total friction (particle + anchor) |

The natural time unit is $\tau = \hat{\gamma}\,\sigma^2/\varepsilon = 1$. Every
timestep, time, and rate below is in these units. Because the units are fixed, the
mapping from the dimensionless inputs (§5) to microscopic parameters is unique and
transparent.

---

## 2. Pair interactions

Two repulsive potentials are available, selected by the `potential` field.

### WCA (Weeks–Chandler–Andersen)

$$U(r) = 4\varepsilon\left[\left(\tfrac{\sigma}{r}\right)^{12} - \left(\tfrac{\sigma}{r}\right)^{6}\right] + \varepsilon, \qquad r < r_\text{cut} = 2^{1/6}\sigma \approx 1.122\,\sigma,$$

with $U(r)=0$ beyond the cutoff. The pair force magnitude is

$$F(r) = \frac{24\varepsilon}{r}\left(\tfrac{\sigma}{r}\right)^{6}\left[2\left(\tfrac{\sigma}{r}\right)^{6} - 1\right].$$

WCA is stiff: already at contact ($r=\sigma$) the force is $24\,\varepsilon/\sigma$.

### Soft sphere (harmonic)

$$U(r) = \tfrac{\varepsilon}{2}\left(1 - \tfrac{r}{\sigma}\right)^2, \qquad F(r) = \frac{\varepsilon}{\sigma}\left(1 - \tfrac{r}{\sigma}\right), \qquad r < r_\text{cut} = \sigma.$$

Linear and soft: a 1% compression below contact needs only $f_0 = 0.01\,\varepsilon/\sigma$.

Forces are computed as $(f_x, f_y) \mathrel{-}= \frac{F(r)}{r}\,(dx, dy)$ per
particle, with **no Newton's-third-law accumulation** — each particle sums its own
force independently so the loop is embarrassingly parallel (a GPU-port choice).

---

## 3. Equations of motion

Each particle $i$ has a position $\mathbf{r}_i$, an orientation angle $\theta_i$,
and an anchor point $\mathbf{a}_i$. The coupled overdamped Langevin system is:

$$\dot{\mathbf{r}}_i = \mu\Big[\underbrace{\mathbf{F}_i^\text{pair}}_{\text{WCA / soft}} + \underbrace{f_0\,\hat{\mathbf{e}}(\theta_i)}_{\text{self-propulsion}} - \underbrace{k_a(\mathbf{r}_i - \mathbf{a}_i)}_{\text{anchor spring}}\Big] + \sqrt{2D}\;\boldsymbol{\eta}_i^T(t),$$

$$\dot{\theta}_i = \sqrt{2 D_r}\;\eta_i^\theta(t), \qquad \hat{\mathbf{e}}(\theta) = (\cos\theta, \sin\theta),$$

$$\dot{\mathbf{a}}_i = \frac{1}{\gamma_a}\,k_a(\mathbf{r}_i - \mathbf{a}_i) + \sqrt{\tfrac{2k_BT}{\gamma_a}}\;\boldsymbol{\eta}_i^a(t).$$

All noises $\boldsymbol{\eta}$ are unit-variance Gaussian white noise,
$\langle \eta_\alpha(t)\eta_\beta(t')\rangle = \delta_{\alpha\beta}\delta(t-t')$.

Key relations (enforce fluctuation–dissipation):

- **Mobility** $\mu = 1/\gamma$ — independent of temperature, so the athermal limit $k_BT\to 0$ stays well defined.
- **Einstein relation** $D = k_BT/\gamma$, hence the translational noise amplitude $\sqrt{2D\,\Delta t} = \sqrt{2k_BT/\gamma\,\Delta t}$.
- **Rotational diffusion** $D_r = 1/\tau_\theta$ sets the persistence time of the active drive. $D_r = 0$ freezes orientations (passive limit).

### Components, switched on/off by parameters

| Term | Active when | Controlled by |
|---|---|---|
| Pair force $\mathbf{F}^\text{pair}$ | always | `potential` |
| Self-propulsion $f_0\hat{\mathbf{e}}$ | $f_0 > 0$ | `delta` (via force balance, §4) |
| Orientational diffusion | $D_r > 0$ | `Pe` → $\tau_\theta$ |
| Anchor spring | $k_a > 0$ | `De` → $k_a$ |
| Anchor friction / motion | $\gamma_a > 0$ | `R` → $\gamma_a$ |
| Thermal noise | $k_BT > 0$ | `C` → $k_BT$ |

---

## 4. The Maxwell viscoelastic anchor

The **spring ($k_a$) + dashpot ($\gamma_a$)** attached to each particle is a
**Maxwell element** — this is where the project name comes from. The particle
feels a restoring force $-k_a(\mathbf{r}_i - \mathbf{a}_i)$ toward its anchor, while
the anchor itself relaxes toward the particle with friction $\gamma_a$ on a
timescale

$$\tau_a = \gamma_a / k_a .$$

For $t \ll \tau_a$ the linkage behaves elastically (the anchor barely moves, so the
spring stores stress); for $t \gg \tau_a$ it behaves viscously (the anchor catches
up and the stress relaxes). That crossover is exactly a Maxwell viscoelastic
response, giving the medium a tunable memory. Anchors are initialized coincident
with their particles (zero initial stretch).

---

## 5. Dimensionless parameterization (what the JSON exposes)

Rather than set microscopic constants directly, you specify **six dimensionless
numbers** plus the particle count `N` and the `potential` type. `Config::recompute`
([src/Config.cpp](../src/Config.cpp)) inverts them into the microscopic
parameters above.

### Inputs

| Field | Symbol | Definition | Sets |
|---|---|---|---|
| `phi` | $\varphi$ | $N\pi\sigma^2 / (4L^2)$, packing fraction in $(0,1)$ | box size $L$ |
| `delta` | $\delta$ | $r^*/\sigma$, typical steady-state pair overlap | active force $f_0$ |
| `Pe` | $\mathrm{Pe}$ | $f_0\,\tau_\theta / (\hat{\gamma}\sigma)$, active Péclet | persistence time $\tau_\theta$ |
| `De` | $\mathrm{De}$ | $(\gamma_a/k_a)/\tau_\theta = \tau_a/\tau_\theta$, active Deborah | spring stiffness $k_a$ |
| `R` | $R$ | $\gamma_a/\gamma$, friction ratio | anchor friction $\gamma_a$ |
| `C` | $C$ | $k_BT/\varepsilon$, dimensionless temperature | thermal energy $k_BT$ |

### Inversion to microscopic parameters

$$\varepsilon = 1,\quad k_BT = C\,\varepsilon,\quad L = \sqrt{\frac{N\pi\sigma^2}{4\varphi}},$$

$$\gamma = \frac{\hat{\gamma}}{1+R},\qquad \gamma_a = R\,\gamma,$$

$$f_0 = f_0(\delta)\ \text{(force balance, §6)},\qquad \tau_\theta = \frac{\mathrm{Pe}\,\hat{\gamma}\,\sigma}{f_0},\qquad k_a = \frac{\gamma_a}{\mathrm{De}\,\tau_\theta}.$$

### Degenerate limits (handled automatically)

- $\delta \ge r_\text{cut}/\sigma$ ⇒ $f_0 = 0$ (passive) ⇒ $\tau_\theta = 0$, $k_a = 0$.
- $\mathrm{Pe} \le 0$ ⇒ $\tau_\theta = 0$ ⇒ no orientational diffusion, $k_a = 0$.
- $\mathrm{De} \le 0$ or $\tau_\theta = 0$ ⇒ $k_a = 0$ (no spring).
- $R = 0$ ⇒ $\gamma_a = 0$ (anchors frozen), $k_a = 0$.

See [Configuration-Reference](Configuration-Reference) for the exact validation
rules and defaults.

---

## 6. Typical pair overlap → active force

The `delta` knob is defined through a steady-state force balance. When two ABPs
swim head-on and stay in contact longer than they reorient, each obeys
$\gamma\dot{\mathbf{r}}_i = f_0\hat{\mathbf{e}}_i - \nabla_{r_i}U$. In steady state
$\dot{\mathbf{r}}_i = 0$, so the active drive balances the repulsion:

$$f_0 = F_\text{pot}(r^*), \qquad \delta \equiv \frac{r^*}{\sigma}.$$

Inverting per potential:

**Soft sphere** — closed form both ways:

$$\boxed{\,f_0 = \frac{\varepsilon}{\sigma}(1 - \delta), \qquad \delta = 1 - \frac{f_0\sigma}{\varepsilon}\,}\qquad (0 < \delta < 1).$$

**WCA** — closed form for $f_0(\delta)$, monotone and trivially invertible numerically:

$$\boxed{\,f_0 = \frac{24\varepsilon}{\sigma}\,\delta^{-7}\!\left(2\delta^{-6} - 1\right)\,}\qquad (0 < \delta < 2^{1/6}).$$

Both return $f_0 = 0$ at or beyond the cutoff (passive limit). The helper
`ForceCalculator::f0ForOverlap(type, delta, eps, sigma)`
([include/ForceCalculator.hpp](../include/ForceCalculator.hpp)) implements this and
is also what the GUI's $\delta$ slider drives.

### Validity of the force-balance picture

1. **Persistent drive:** reorientation time $\tau_\theta$ exceeds the pair
   relaxation time $\tau_\text{pair} \sim \gamma\sigma/F'(r^*)$.
2. **Athermal limit:** $k_BT \ll \varepsilon$, so thermal kicks don't smear the
   contact distance (finite $C$ broadens the overlap distribution around $\delta$).
3. **Pairwise contact:** exact for a head-on pair; a good estimate at low $\varphi$,
   shifted by three-body crowding at high density.

---

## 7. Boundary conditions

The system lives in a square periodic box of side
$L = \sqrt{N\pi\sigma^2/(4\varphi)}$. Pair separations use the minimum-image
convention and positions are wrapped back into the primary cell each step
([include/Box.hpp](../include/Box.hpp)). Neighbor finding uses a sort-based cell
list with a Verlet skin — see [Integrators](Integrators#cell-lists).

---

See also: **[Integrators](Integrators)** for how these SDEs are discretized, and
**[Configuration-Reference](Configuration-Reference)** for every field and default.
