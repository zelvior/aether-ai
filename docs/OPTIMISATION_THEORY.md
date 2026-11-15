# AETHER — Optimisation Theory and Hyperparameter Transfer

Status: **Analysis and proposal.** No run exists. μP has not been implemented or tested in AETHER. The transfer
claim this document examines is one the project already relies on, and it may be wrong.

Related: [`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) (the optimiser) ·
[`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md) (derivations) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A (hyperparameters) ·
[`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) (how this would be tested) ·
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §7 (why tuning is unaffordable)

---

## 1. The problem this document exists to solve

[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.3 contains this admission, buried in an `[OPEN]` marker:

> AETHER cannot afford a sweep at Config M scale. The learning rate will be selected on Config T and
> Config N and then **transferred without verification**.

**That is a load-bearing assumption the project had not examined.** It says, in effect: *the optimal learning
rate for a 228 k-parameter model is the optimal learning rate for an 8.4 M-parameter model.*

Under the **standard parameterisation**, this is **false** — and the reason is well understood. Under the
**maximal update parameterisation (μP)**, it is approximately **true by construction** `[S50]`.

AETHER is currently assuming the conclusion of a theorem it has not adopted the hypotheses of.

---

## 2. Why the standard parameterisation breaks transfer

### 2.1 The instability argument

Consider a linear layer `y = Wx` with `W ~ N(0, σ²)` and `x` having unit-variance entries. Each output:

```
y_j = Σ_{i=1}^{d_in} W_ji x_i        ⇒   Var(y_j) = d_in · σ²
```

With the standard `σ² = 1/d_in` init, `Var(y_j) = 1` — stable at initialisation. But during training, a
gradient step changes each `W_ji` by `η·g_ji`, and the resulting change in `y` is:

```
Δy_j = Σ_i ΔW_ji x_i     ⇒   Var(Δy_j) = d_in · η² · Var(g)
```

**The update magnitude scales with `√d_in`.** As width grows, a fixed learning rate produces larger and larger
effective updates relative to the signal — until the model diverges.

This is the mechanism behind the well-known observation that large Transformers need smaller learning rates,
and it is why "tune on the small model, transfer up" fails: the small model's optimum is **too large** for the
big one.

### 2.2 What this means for AETHER concretely

Config T → Config M is a **36.9× parameter increase**, and width goes `64 → 256` (4×). If the learning rate
tuned on Config T were transferred unchanged, the effective update magnitude at Config M would be roughly
`√4 = 2×` too large in the projection layers.

| Transfer | Width ratio | `√` (update inflation) |
| --- | --- | --- |
| T → N | 2× | 1.41× |
| N → M | 2× | 1.41× |
| T → M | **4×** | **2.00×** |

**[PROPOSED]** This is not a divergence guarantee — residual connections, RMSNorm, and Adam's adaptive
scaling all damp it. But it is a systematic bias in one direction, and AETHER's current plan does not correct
for it at all.

---

## 3. Maximal Update Parameterisation (μP)

`[S50]` (Tensor Programs V) establishes that under a specific reparameterisation, **optimal hyperparameters
become stable as width grows**, enabling zero-shot transfer from a small proxy model to a large target.

### 3.1 The width-dependent rules

For a layer `y = Wx` with `d_in` inputs, μP requires:

| Quantity | Standard | **μP** |
| --- | --- | --- |
| Init variance `σ²` | `1/d_in` | `1/d_in` (unchanged) |
| **Forward multiplier** | 1 | **1** (for most layers) |
| **Learning rate** | `η` | **`η · (d_base/d_in)`** |
| **Output-layer learning rate** | `η` | **`η · (d_base/d_in)`** |
| **Attention `1/√d_h` scaling** | `1/√d_h` | **`1/d_h`** with adjusted init |
| Adam epsilon | `ε` | `ε` (unchanged) |
| Adam `β` | fixed | fixed |

The two deviations from what AETHER currently specifies are:

1. **Per-layer learning rate scaling by fan-in**, replacing one global learning rate.
2. **`1/d_h` attention scaling** rather than `1/√d_h`.

Point 2 conflicts directly with `[S1]`'s scaled dot-product attention. This is not a contradiction — μP changes
the *parameterisation* so that the limit is well-behaved as width → ∞, and in that limit the softmax saturates
differently. At finite, small width the distinction may or may not matter.

### 3.2 What μP would buy AETHER

| Without μP | With μP |
| --- | --- |
| Tune on T, hope it transfers to M | Tune on T, **transfer justified by a scaling rule** |
| One global learning rate | Per-layer rates from a formula |
| Transfer bias `~√(width ratio)` | Transfer bias approximately **zero in the limit** |
| Tuning cost at M: unaffordable | Tuning cost at M: **still zero** |

That last row is why μP is relevant to AETHER rather than merely interesting: **AETHER's inability to tune at
Config M is exactly the problem μP was invented to solve.**

### 3.3 The honest limitations

| Limitation | Detail |
| --- | --- |
| Proven in the infinite-width limit | Finite-width deviation exists and is unquantified |
| Validated mainly on Transformers at 10¹–10¹⁰ params | AETHER sits at the low end of that range |
| `[S50]` transfers from 13 M → 350 M and 40 M → 6.7 B | AETHER would transfer **up** from 0.23 M — far below any validated point |
| Requires reparameterising the model | Changes `ARCHITECTURE_SPEC` §4.3 and §8A.3 |
| Does **not** fix data-limited regimes | AETHER may be data-limited ([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) E3) |

**[PROPOSED]** μP is a genuine candidate for AETHER, and the current documentation's silent assumption of
learning-rate transfer is strictly worse than either adopting μP or explicitly testing the assumption.

---

## 4. The three options, costed

| Option | Cost | Risk | Verdict |
| --- | --- | --- | --- |
| **O1** Transfer LR unchanged (current plan) | 0 | Systematic bias, unquantified | **Status quo — should not survive** |
| **O2** Adopt μP | Implementation + verification | Untested at AETHER's width | **Strong candidate** |
| **O3** Test transfer empirically | ≈ 2 extra Config N runs | Small | **Minimum acceptable** |

### 4.1 Costing O3

The cheapest defensible position: train Config N at two learning rates, one of which is the Config T optimum
and one of which is that optimum scaled by the `√` correction. If the scaled value wins at N, the bias is real
and O2 should be adopted.

| Run | Config | `D` | FLOPs | @10 GFLOP/s |
| --- | --- | --- | --- | --- |
| N @ `η_T` | N | 9.2 M | 1.35 × 10¹⁴ | 3.8 h |
| N @ `η_T/√2` | N | 9.2 M | 1.35 × 10¹⁴ | 3.8 h |
| **Total** | | | **2.71 × 10¹⁴** | **7.5 h** |

**7.5 hours** to test whether AETHER's central hyperparameter assumption holds. That is a rounding error
against a 5-day experiment programme and should be added to it.

---

## 5. Learning-rate schedules, derived

### 5.1 Cosine decay

```
η(t) = η_min + ½(η_max − η_min)(1 + cos(π t / T_total))
```

`[S41]` (SGDR) motivates cosine shape; AETHER uses it **without restarts**, because a monotone schedule is
easier to make exactly resumable ([`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §6).

**Why restarts are declined:** a restart requires the schedule to know the total run length at every point,
which conflicts with resuming a run whose remaining length has changed. The benefit of restarts is
unestablished for language modelling anyway.

### 5.2 Warm-up — and why AETHER omits it

Standard practice warms up over 1–5 % of steps. `[S27]` shows this is **necessary for post-norm** Transformers
(whose initialisation-time gradients are large and depth-independent) but **unnecessary for pre-norm**.

AETHER is pre-norm (§4.1 of [`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md)), so it omits warm-up.

**[ASSUMPTION]** `[S27]`'s result holds at `d = 256, L = 8`. It was demonstrated at BERT scale. If training
proves unstable in the first few hundred steps, adding warm-up is the first remedy and this assumption should be
recorded as having failed.

### 5.3 The interaction nobody tests

Warm-up and μP interact: μP keeps the *update scale* stable across width, and warm-up compensates for an
initialisation-time transient. A model using both may have neither problem, or may have a different one.

**AETHER does not know which, and says so.**

---

## 6. Gradient clipping

Global-norm clipping:

```
if ‖g‖₂ > c:  g ← g · c / ‖g‖₂            c = 1.0 proposed
```

**Why `c = 1.0` and not a tuned value:** the gradient norm at initialisation is approximately predictable from
§7, and clipping only engages on outliers. `[PROPOSED]`, untested.

**The interaction with μP is a real hazard.** Under standard parameterisation, gradient norms grow with width,
so a fixed `c` clips more aggressively at larger `d`. Under μP they do not, so `c` means the same thing at every
width. **A fixed clipping threshold is itself a width-dependent hyperparameter unless μP is used** — a point
AETHER had not noticed before this analysis.

---

## 7. Expected gradient magnitude at initialisation

For the output head with `V = 8192`, entropic loss `≈ ln V = 9.01` nats at initialisation, and gradient
`∂L/∂z_j = p_j − δ_{jt}`:

```
‖∂L/∂z‖₂² = (1 − p_t)² + Σ_{j≠t} p_j²
```

With `p` near-uniform (`p_j ≈ 1/V`):

```
≈ 1 + V·(1/V)² = 1 + 1/V ≈ 1.0001        ⇒  ‖∂L/∂z‖ ≈ 1
```

So the head's output gradient has **unit norm at initialisation**, and `‖W_head‖` must convert that to a hidden
gradient of scale `√d`-ish. The `1/√d` init gives `‖W‖_F ≈ 1`, so the hidden gradient is also `O(1)`.

**This is why `c = 1.0` is a defensible default**: at initialisation the gradient norm is already about 1, so
clipping engages only if something goes wrong.

**[PROPOSED]** It is *not* a guarantee — clipping engages during legitimate transient spikes too, and the
threshold should be revisited once a real loss curve exists.

---

## 8. What AETHER should do

| # | Action | Cost |
| --- | --- | --- |
| 1 | **Delete the silent transfer assumption** from `ARCHITECTURE_SPEC` §8A.3 | 0 |
| 2 | Run O3 (two Config N runs at different LR) | 7.5 h |
| 3 | If the bias is real, adopt μP for Phase 5 | implementation |
| 4 | Record the decision either way in the model card | 0 |

Action 1 is free and should happen regardless. Actions 2–3 are cheap and consequential.

---

## 9. Unresolved questions

1. Is the learning-rate transfer bias real at AETHER's widths (64 → 256)? **O3 answers this.** **[OPEN]**
2. Does μP's `1/d_h` attention scaling break `[S1]`'s attention at `d_h = 32`? **[OPEN]**
3. Is μP validated at *smaller* widths than its papers study? **Genuinely unknown — the papers transfer upward from 13 M.** **[OPEN]**
4. Should gradient clipping be width-dependent even without μP? **[OPEN]**
5. Does warm-up interact with μP such that pre-norm + μP is worse than pre-norm alone? **[OPEN]**
6. Is `β₂ = 0.95` stable across widths, or is it another width-dependent hyperparameter? **[OPEN]**

---

## 10. Status summary

| Item | Status |
| --- | --- |
| Update-scale argument (`√d`) | **Derived** — §2.1 |
| Transfer bias at 4× width ≈ 2× | **Derived** — §2.2 |
| μP rules | **Established** from `[S50]` |
| μP validated at AETHER's width | **No — below every validated point** |
| Current plan's transfer assumption | **Unjustified; should be removed** |
| Cost to test it | **7.5 h** |
| Gradient norm at init ≈ 1 | **Derived** — §7 |
| Any run | **None.** |
