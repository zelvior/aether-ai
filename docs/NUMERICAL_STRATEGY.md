# AETHER — Numerical Strategy

Status: **Proposal.** No kernel has been written against this document, so every claim about
numerical behaviour is a design intent until Phase 4–6 validate it.

This document specifies the numeric types, accumulation rules, overflow handling, and determinism
policy for AETHER. It exists because **32-bit x86 is numerically awkward in ways that 64-bit
development machines hide** (§2), and a runtime that is correct on x86-64 can produce different
results — or undefined behaviour — on i386.

---

## 1. Requirements

| # | Requirement | Consequence |
| --- | --- | --- |
| N1 | Output must be deterministic for fixed input on a fixed build | No unseeded randomness, no thread-order dependence in reductions |
| N2 | Scalar and vector paths must agree within a stated tolerance | Equivalence tests per kernel |
| N3 | No silent overflow, NaN, or inf | Explicit saturation or rejection, documented per operation |
| N4 | The 32-bit build's results must be comparable to the 64-bit build's | A defined comparison protocol, not "should be the same" |
| N5 | No dependency on FPU evaluation precision beyond what the standard guarantees | See §2.3 |
| N6 | Narrow formats must not be used where the target cannot compute them natively | See §3 |

---

## 2. The x87 problem — why this document has to exist

### 2.1 Extended precision

On i386, floating-point may be evaluated on the x87 FPU, whose registers hold **80-bit extended
precision** (`long double`, 64-bit significand). C exposes the effective evaluation policy through
`FLT_EVAL_METHOD` (`<float.h>`):

| `FLT_EVAL_METHOD` | Meaning |
| --- | --- |
| `0` | Evaluate all floating expressions in their own type — **SSE2 on x86-64** |
| `1` | Evaluate `float` and `double` as `double` |
| `2` | Evaluate everything as `long double` — **common x87 with `-mfpmath=387`** |
| `-1` | Indeterminate |

### 2.2 Why it matters

Consider `s = a*b + c`, all `binary32`. Under `FLT_EVAL_METHOD == 0`, the product is rounded to
`binary32` before the add. Under `FLT_EVAL_METHOD == 2`, the product stays in 80-bit precision and is
rounded after the add. The two results can differ in the last place.

Consequences specific to AETHER:

- **A dot-product reduction** accumulates differently on i386 than on x86-64, so attention logits
  differ slightly, so softmax differs, so the final token distribution can differ at the last place.
  Usually harmless. Occasionally, at a decision boundary, it changes a sampled token.
- **Reproducibility** breaks: the same source, compiled two ways, gives two answers
  ([`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §1).
- **Equivalence testing** becomes ambiguous unless the tolerance and the evaluation policy are both
  stated.

### 2.3 Policy

**[PROPOSED] N-P1. Store all floating-point values in `binary32`; never rely on extended
intermediates.**

- All tensors, buffers, and struct fields holding model values are `float` (`binary32`).
- Intermediate values are held in `float` locals, not `double` or `long double`.
- Where an intermediate must be widened for accuracy (accumulation, §4), it is widened **explicitly
  and locally**, with the reason documented at that site, and the widened value is rounded back to
  `binary32` at a defined point — not left to the FPU.

**[PROPOSED] N-P2. Compile the i386 build with SSE2 when the target supports it, and verify
`FLT_EVAL_METHOD == 0`; treat the x87 path as a correctness fallback with an explicitly larger
tolerance.**

The runtime performs a CPUID check and selects a path. What AETHER may **not** do is assume x86-64-like
evaluation on i386.

**[PROPOSED] N-P3. The evaluation policy actually in force is recorded in every benchmark and
evaluation report**, alongside the compiler, flags, and target. A result with an unstated
`FLT_EVAL_METHOD` is not a reproducible result.

**[OPEN]** Whether `-ffloat-store` (which forces rounding to `binary32` after each assignment) is
sufficient to make the x87 path agree with SSE2, and at what cost, is unmeasured. It is a Phase 7
experiment.

---

## 3. Supported numeric types

| Type | Role | Phase | Justification |
| --- | --- | --- | --- |
| `binary32` (`float`) | **Compute and accumulation** | 4–9 | Native on x87, SSE, and SSE2. Universal. |
| `float64` (`double`) | **Host-side tooling only** (loss computation sanity checks, reference implementations, test oracles) | 4–9 | Not in the inference path; used to catch `binary32` mistakes during development |
| `int8` | Weight **storage** only | 8 | Halves bandwidth; no native dot-product on target |
| `int4` | Weight **storage** only, packed | 8 | Further bandwidth reduction; unpacking cost must be measured |
| `binary16` | **Not supported** | — | No native i386 arithmetic; conversion cost with no compute benefit (§4.1) |
| `bfloat16` | **Not supported as a compute type** | — | Same reason; candidate as an optimiser-state storage format in Phase 8 only |
| `long double` | **Forbidden in model code** | — | Non-portable width across targets; breaks determinism |

### 3.1 Why fp16 and bf16 are excluded

Both are 16-bit formats with IEEE-style layouts; bf16 keeps fp32's 8-bit exponent with a 7-bit
significand, fp16 has a 5-bit exponent with a 10-bit significand and a maximum finite value of 65504
`[S26]`.

On AETHER's targets **neither has native arithmetic**. Using them means converting to `binary32`,
computing, and converting back — which costs instructions and buys nothing. Their benefit on GPUs
comes from tensor cores, which do not exist here.

The `binary32` storage cost is already trivially small for AETHER (§[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §3),
so there is no memory pressure forcing a 16-bit format. The honest position is: **excluded for lack of
benefit, not for lack of interest**, and revisit if a target appears with native support.

---

## 4. Accumulation precision

### 4.1 Floating-point accumulation

**[PROPOSED] N-P4. Accumulate dot products in `binary32`, but in a fixed, documented order.**

Why not `double`: doubling accumulator width doubles register pressure and, on x87, pushes values into
memory rather than registers. On a small model with few accumulations, `binary32` accumulation error
is small relative to quantisation and training noise. This is an **[ASSUMPTION]** — the error budget
has not been analysed numerically, and Phase 8 should measure it.

Why order matters: floating-point addition is not associative. `(a+b)+c ≠ a+(b+c)` in general. If the
reduction order differs between the scalar and vector paths, the results differ, and N2 fails.

**[PROPOSED] N-P5. The reduction order is part of the kernel contract.** Each kernel documents its
order (sequential, pairwise, blocked-by-`k`). A vector path may use a different internal order **only**
if it passes the equivalence test at the stated tolerance (§6).

### 4.2 Methods for improving accuracy without `double`

If Phase 8 finds `binary32` accumulation inadequate:

1. **Pairwise (cascading) summation** — `O(log n)` error growth instead of `O(n)`, at negligible cost,
   and order is deterministic by construction. **This is the preferred first step.**
2. **Kahan / Neumaier compensated summation** — near-quadrupling of effective precision, roughly 4×
   the additions. Suitable for the output head, where `V = 8192` and the sum is long.
3. **Widening only the accumulator** — `double` accumulator, `float` operands. Costs register pressure
   and defeats SIMD packing.

No decision is made now; the choice depends on measurement.

### 4.3 Integer accumulation

**[PROPOSED] N-P6. int8 products accumulate in `int32`.**

Bound: with operands of magnitude ≤ 127, the worst-case product is 16129. An `int32` accumulator
saturates at 2 147 483 647, so overflow requires a reduction length `K > 133 077`. Every AETHER block
dimension (`d ≤ 256`, `d_ff ≤ 1024`, `V = 8192`) is far below this.

- `int32` accumulation is **safe by construction** for all planned dimensions, with a documented
  bound rather than hope.
- `int16` accumulation is **not** used: it would overflow at `K > 8` and require per-block magnitude
  bounds plus runtime checks, which cost more than the width saved.
- `int64` accumulation is **not** used: on i386, 64-bit multiply and add are emulated, and the bound
  above shows it is unnecessary.

The bound is checked at format-load time: if a model declares a dimension exceeding the safe limit,
the loader **rejects** it rather than overflowing ([`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §6).

---

## 5. Overflow, underflow, and catastrophic cancellation

### 5.1 Softmax

The naive form `exp(x_i) / Σ exp(x_j)` overflows `binary32` for any `x_i > 88.72` (`exp` returns
`+inf`), and underflows to zero for `x_i < -103.97`. Both produce NaN or silent zeros.

**[PROPOSED] N-P7. Max-subtraction is mandatory and is part of the kernel contract, not an
optimisation.**

```
m = max_i x_i
e_i = exp(x_i - m)          // e_i ∈ (0, 1], at least one e_i == 1
p_i = e_i / Σ_j e_j
```

This makes the largest exponent exactly `1`, guarantees no overflow, and guarantees the denominator
is `≥ 1`. An implementation that omits it is **wrong**, not merely less accurate.

Edge cases with defined behaviour:

| Case | Required behaviour |
| --- | --- |
| All `x_i = -inf` (fully masked row) | Defined by caller; must not produce NaN. AETHER's contract: reject any attention row with zero unmasked keys |
| Any `x_i = +inf` | Reject the model file or the computation; do not propagate silently |
| Any `x_i = NaN` | Propagate and be detectable; a NaN in the score buffer is a bug to be surfaced, not masked |
| Denominator `= 0` | Impossible under this scheme (`≥ 1`, unless NaN present) |

### 5.2 Sigmoid and SiLU

`σ(x) = 1/(1+exp(-x))` overflows `exp` for `x < -88.72`, giving `1/(1+inf) = 0` — which is
*arithmetically correct* as the limit, but produces a division by infinity rather than a defined
result on some implementations. SiLU is `x·σ(x)`; for very negative `x`, `x·0 = 0` is correct.

**[PROPOSED] N-P8. Sigmoid uses a branch that avoids denominator overflow:**

```
σ(x) = 1/(1+exp(-x))        for x ≥ 0
σ(x) = exp(x)/(1+exp(x))    for x < 0
```

Both branches keep `exp`'s argument non-positive, so no overflow is possible. This is standard and
costs one branch, which is predictable and cheap relative to `exp`.

### 5.3 Cross-entropy / log-softmax

Computing `log(softmax(x))` naively loses precision: `softmax` can underflow to `0`, and `log(0)` is
`-inf`.

**[PROPOSED] N-P9. Use the log-sum-exp form with max-subtraction:**

```
m      = max_i x_i
lse    = m + log( Σ_i exp(x_i - m) )
log p_i = x_i - lse
loss   = lse - x_target
```

The loss is `lse - x_target`, never `-log(p_target)`. This is exact for large losses and stable for
small ones.

### 5.4 Catastrophic cancellation in RMSNorm

`RMSNorm(x) = x / sqrt(mean(x²) + ε)`. The sum of squares can overflow for large `x`: with
`x ~ 10¹⁹`, `x²` overflows `binary32`'s range (`~3.4 × 10³⁸` at `x ≈ 1.8 × 10¹⁹`).

**[PROPOSED] N-P10.** Inputs to normalization are the output of a residual stream that is bounded in
practice; the runtime nevertheless guards the sum of squares and rejects non-finite results rather
than propagating them. If a training run produces non-finite normalization state, that is a reported
failure, not a silent `NaN`.

`ε = 1e-5` is used, which also bounds the denominator away from zero for near-zero inputs.

### 5.5 RoPE and trigonometric precision

RoPE `[S24]` requires `cos(t·θ_i)` and `sin(t·θ_i)` for position `t` and frequency `θ_i = Θ^{-2i/d_h}`.

- Computing `t·θ_i` for `t = 2047` and small `θ_i` in `binary32` loses precision in the argument, and
  `sin`/`cos` amplify argument error.
- **Precomputation is required**: a table of `sin`/`cos` per position up to `T_max` per frequency pair.

**[PROPOSED] N-P11. Precompute the RoPE table in `float64` at load time, store as `binary32`.**
This uses the wider type where it is free (once, at start-up, not in the hot loop) and keeps the
decode loop narrow. Table size: `T_max × d_h` floats per pair = `2048 × 256 × 4 B = 2 MiB` for
Config M — acceptable, and it is included in the runtime overhead budget
([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.3 as part of the activation/scratch allocation).

**[OPEN]** Whether this table's `binary32` storage is accurate enough at `t = 2047` is unverified. A
`float64` table (4 MiB) is the fallback if not.

---

## 6. Scalar/vector equivalence

### 6.1 The rule

**[PROPOSED] N-P12. Every vectorised kernel must be validated against its scalar counterpart, for
the same inputs, at a stated tolerance. A kernel without an equivalence test does not ship.**

| Kernel | Tolerance | Basis |
| --- | --- | --- |
| Elementwise (`+`, `×`, SiLU, RMSNorm scaling) | **Exact bit equality** | No reduction; operations are identical |
| Dot products / matmul | `\|a−b\| ≤ 1e-5 · max(1, \|a\|)` per element | Different reduction order |
| Softmax | `1e-5` absolute per probability | Amplifies dot-product error |
| Full forward pass | `1e-4` relative on logits, `1e-3` on sampled-token agreement over 1000 tokens | Compounding |

These tolerances are **proposals**. They are not derived from an error analysis; they are engineering
starting points that Phase 4 must either validate or tighten.

### 6.2 Why "bit identical" for elementwise

Elementwise operations with the same operand order, on the same type, must produce identical results.
If they do not, the vector path has introduced an extra rounding step or altered the operation — a
real bug, not a tolerance question. Insisting on exactness here lets the dot-product tolerance be
justified rather than absorbing unidentified defects.

### 6.3 Dispatch policy

**[PROPOSED] N-P13.**

1. The **scalar path is the reference** and is always compiled.
2. Vector paths are selected at **runtime** by CPUID feature detection, never at compile time only,
   because a binary built with SSE2 must still run correctly on a target without it — or fail with a
   clear message, which is preferable to `SIGILL`.
3. An environment override forces the scalar path, for debugging and for the equivalence harness.
4. Every vector path has a `#define`-free runtime switch so a bug is isolatable without a rebuild.

---

## 7. Determinism

### 7.1 Sources of nondeterminism

| Source | Status | Mitigation |
| --- | --- | --- |
| Thread scheduling in reductions | **Avoided**: single-threaded inference in Phase 4–6 | Document; parallel reductions join in a fixed tree order when added |
| Reduction order across builds | Present | Order is part of the kernel contract (N-P5); tolerance-based tests (§6) |
| x87 extended precision | Present on i386 | §2.3 policy; larger tolerance for the x87 path |
| Uninitialised memory | Bug class | Zero-initialise every buffer at allocation; valgrind/asan in test matrix |
| `exp`/`log`/`sin` implementation variance | Present across libm implementations | **Explicitly documented**: AETHER does not guarantee bit-identical transcendental results across libm versions |
| Sampling randomness | By design | Seed recorded; `greedy` is fully deterministic |
| Unordered hash iteration in tokenizer | Bug class | Tokenizer uses ordered structures only ([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §6) |

### 7.2 What AETHER promises, precisely

**[PROPOSED] N-P14.**

- **Same binary, same machine, same input, greedy decoding → identical output.** This is a hard
  requirement and is testable.
- **Different binary (e.g. 32-bit vs 64-bit), same input → same output within the tolerances of §6**,
  with a documented report of the observed maximum deviation. Exact equality is **not** promised and
  would be a false claim on a target with a different FPU evaluation model.
- **Different libm → not guaranteed**, and this is stated rather than glossed over.

This is deliberately weaker than "reproducible builds produce reproducible outputs", because that
claim would be false for a system using transcendental functions across a 32/64-bit boundary.

---

## 8. Integer quantisation strategy (Phase 8 preview)

Stated here so that the format and runtime do not preclude it. **Not implemented, not evaluated.**

| Aspect | Proposed approach | Rationale |
| --- | --- | --- |
| Granularity | Per-output-channel symmetric | Simple, well-understood, no zero-point bookkeeping in the hot loop |
| Weight quantisation | `q = round(w / s)`, `s = max\|w\| / 127` per channel | Symmetric avoids zero-point arithmetic |
| Dequantisation | `w ≈ q · s` accumulated in `binary32` | Keeps the dot product in `binary32`; §4.3 applies only if an integer dot-product kernel is used |
| Activation quantisation | **Not proposed initially** | `[S17]`'s outlier problem is harder without native int8 dot products |
| Calibration | Per-channel max from a held-out calibration set, recorded | Required for reproducibility |
| Error measurement | **Mandatory**, against the unquantised model, on the same evaluation | Refusing to report would violate [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §4 |

**On speedups:** the literature reports large speedups from int8 and int4 `[S15][S16][S17][S18]`. Those
come from tensor cores, AVX2+, or integer-dot-product units. **AETHER's targets have none of these.**
The realistic benefit here is **halved memory traffic**, which helps a bandwidth-bound decode loop —
and that must be measured, not assumed. Any AETHER document claiming a compute speedup from
quantisation before measuring one would be violating the project's own principles.

---

## 9. Error budget: a first-order analysis

Phase 2 originally listed this as unknown. It is not unknown in the first order — floating-point error
in a dot product has a classical bound, and applying it is a half-hour of arithmetic that should have
been done before the spec was published.

### 9.1 The bound

For a dot product of length `n` computed in floating point with unit roundoff `u`, the standard result
(Higham's `gamma_n`) is

```
|fl(a·b) − a·b|  ≤  gamma_n · Σ|a_i b_i|  ≤  gamma_n · ‖a‖ ‖b‖
gamma_n = n·u / (1 − n·u)
```

For `binary32` in round-to-nearest, `u = 2⁻²⁴ = 5.96 × 10⁻⁸`.

### 9.2 Applied to AETHER's reduction lengths

| Reduction | `n` | `gamma_n` |
| --- | --- | --- |
| Attention score (per head) | 32 | 1.91 × 10⁻⁶ |
| Hidden projection (`d`) | 256 | 1.53 × 10⁻⁵ |
| SwiGLU down (`d_ff`) | 688 | 4.10 × 10⁻⁵ |
| Output head (`V`) | 8192 | **4.89 × 10⁻⁴** |

**The output head is the dominant error source**, by more than an order of magnitude over every other
reduction, purely because its reduction length is 32× the hidden dimension. This is a concrete,
actionable finding: if `binary32` accumulation proves inadequate anywhere, it will be here first.

### 9.3 Magnitude of the resulting error

The bound is on *relative* error scaled by the sign-conditional sum. If intermediate magnitudes are
`O(1)` — which they are after RMSNorm, whose output has unit RMS by construction — the worst-case
absolute error on a logit is `gamma_n` times the condition number of the dot product.

| Condition number `κ` | Head logit error | Hidden logit error |
| --- | --- | --- |
| 1 | 4.9 × 10⁻⁴ | 1.5 × 10⁻⁵ |
| 10 | 4.9 × 10⁻³ | 1.5 × 10⁻⁴ |
| 100 | 4.9 × 10⁻² | 1.5 × 10⁻³ |

Note `κ = Σ|a_i b_i| / |a·b|` can be large when terms cancel. **This is the worst case, not the
typical case**; random-sign sums have `κ ≈ 1` in expectation and the error is much closer to
`sqrt(n)·u ≈ 1e-4` for the head.

### 9.4 Effect on the softmax and on token selection

Softmax is locally well-conditioned:

```
dP_i / P_i ≈ dlogit_i        (for small perturbations)
```

So a logit error of `ε` shifts every probability by about `0.01 %·(ε/1e-4)`. A **token-selection
change** requires the top-1/top-2 logit margin to be smaller than roughly `2ε`:

| Logit error `ε` | Probability shift | Token flips require margin < |
| --- | --- | --- |
| 1.5 × 10⁻⁵ (hidden) | ~0.0015 % | 3.0 × 10⁻⁵ |
| 4.9 × 10⁻⁴ (head, κ=1) | ~0.05 % | 9.8 × 10⁻⁴ |
| 4.9 × 10⁻³ (head, κ=10) | ~0.5 % | 9.8 × 10⁻³ |

**Implication for the equivalence tolerances in §6.1:** the proposed `1e-3` logit tolerance is
*too loose* to catch a head-accumulation defect, and the `1e-3` token-agreement tolerance is *about
right* — a few tokens in a thousand flipping is consistent with `ε ≈ 1e-3`, which is what a real
defect would produce. A tighter logit tolerance would fail spuriously on the x87 path; a looser one
would hide genuine bugs.

### 9.5 Accumulated error across layers

Errors do not compound linearly, because each layer re-normalises its input (RMSNorm bounds the
magnitude). First-order estimates for `L` layers:

| `L` | Per-layer `gamma_256` | Quadrature (independent) | Linear (systematic) |
| --- | --- | --- | --- |
| 4 | 1.53 × 10⁻⁵ | 3.1 × 10⁻⁵ | 6.1 × 10⁻⁵ |
| 8 | 1.53 × 10⁻⁵ | 4.3 × 10⁻⁵ | 1.2 × 10⁻⁴ |

RMSNorm between layers is what keeps this small. **Without normalisation this analysis would be
meaningless**, because the residual stream would grow and `κ` with it.

### 9.6 Attention logits at initialisation

With RMSNorm ensuring unit-RMS activations and weight initialisation `N(0, 1/d)`:

- each `q_j ~ N(0, d·s²) = N(0, 1)`, so `Var(q_j) = 1`
- `q·k = Σ_{d_h} q_j k_j` gives `Var = d_h · 1 = 32`, so `std = 5.66`
- after the `1/√d_h` scaling, **logit std ≈ 1.0**

So softmax arguments are `O(1)` at initialisation, with a factor of ~89 of headroom before `exp`
overflows `binary32`. And with max-subtraction (§5.1) the argument is *always* `≤ 0`, so **overflow is
structurally impossible at any scale** — the headroom is a fallback, not the guarantee.

### 9.7 What remains genuinely unknown

| Question | Status |
| --- | --- |
| Whether the *worst-case* `κ` occurs in practice on real activations | **Unmeasured** — needs instrumentation on a trained model |
| Whether `binary32` head accumulation degrades loss measurably | **Unmeasured** |
| Actual x87-vs-SSE2 divergence magnitude | **Unmeasured** |
| int8 weight-quantisation quality loss at 8 M parameters | **Unmeasured** |
| RoPE table precision at maximum position | **Unmeasured** |
| Memory-ordering effects of pairwise vs sequential summation on final loss | **Unmeasured** |

The analysis above bounds the *arithmetic*. It cannot substitute for measuring a trained model, and
nothing here is presented as if it could.


---

## 9A. Quantisation error: a separate budget

Phase 8 proposes int8 weight storage ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.2). §9 above bounds
*arithmetic* error in `binary32`; it says nothing about *representation* error from quantising weights,
and the two differ by orders of magnitude.

### 9A.1 Simulated reconstruction error

`N(0, 1/√d)` initialisation, symmetric int8 (`scale = max|w| / 127`), relative Frobenius reconstruction
error per tensor at Config M's actual shapes:

| Tensor | Shape | Per-tensor | Per-channel |
| --- | --- | --- | --- |
| `attn.wqkv` | 768 × 256 | 0.0068 | 0.0069 |
| `attn.wo` | 256 × 256 | 0.0070 | 0.0069 |
| `mlp.wgateup` | 1376 × 256 | 0.0069 | 0.0070 |
| `mlp.wdown` | 256 × 688 | 0.0076 | 0.0076 |
| head (tied) | 256 × 8192 | 0.0090 | 0.0090 |

**[PROPOSED, SIMULATED]** These come from a random-variable simulation, not from AETHER's trained
weights (which do not exist). They are indicative of magnitude, not a measurement of this model.

**Per-channel quantisation gains nothing here**, because Gaussian initialisation gives every row the
same scale. It would matter for trained weights with heterogeneous row norms — a Phase 8 question.

### 9A.2 Propagation through the stack

Eight residual layers, each introducing its own weight error:

| Contributors | Quadrature (independent) | Linear (systematic) |
| --- | --- | --- |
| 1 layer | 0.0074 | 0.0074 |
| 4 layers | 0.0148 | 0.0296 |
| 8 layers | **0.0210** | 0.0592 |

RMSNorm between layers bounds growth ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §4.7), so the
quadrature column is the realistic estimate: **≈ 0.021 relative at the output.**

### 9A.3 The comparison that matters

| Error source | Magnitude | Ratio to `gamma_256` |
| --- | --- | --- |
| `binary32` arithmetic, `d = 256` | 1.53 × 10⁻⁵ | 1× |
| `binary32` arithmetic, `V = 8192` | 4.89 × 10⁻⁴ | 32× |
| **int8 weights, 8 layers** | **≈ 2.1 × 10⁻²** | **≈ 1,370×** |

**Quantisation error exceeds the largest arithmetic error by roughly three orders of magnitude**, and
the smallest arithmetic error by nearer four.

### 9A.4 Consequence for equivalence testing

`EVALUATION_PLAN.md` §5 specifies a 32-bit-vs-64-bit tolerance of **1e-3 relative**. That tolerance is
correct for what it tests — the same arithmetic performed on different FPUs — but
[`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §4 classifies a > 1e-3 difference as a **failure**.

**Those two rules collide in Phase 8.** An int8 model compared against its fp32 reference will differ by
≈ 2.1 × 10⁻², which the current rules would score as a failure — even when quantisation is working
correctly.

The fix is a **second, separate tolerance**, and this document proposes it:

| Comparison | Tolerance | Rationale |
| --- | --- | --- |
| fp32 x87 vs fp32 SSE2 | 1e-3 rel, ≥ 99 % greedy agreement | §6.1 — arithmetic only |
| **int8 vs fp32** | ****not yet specified** | Must be set from measurement, not arithmetic |

**[PROPOSED]** The int8 tolerance cannot be chosen analytically: §9A.2 gives a *bound*, not a
distribution, and per-tensor quantisation interacts non-linearly with softmax and sampling. It must be
measured on a real quantised model in Phase 8 and **written down before the first comparison** — the
same pre-registration discipline as [`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §4.1.

**What would make int8 unacceptable:** if the measured BPC degradation exceeds a pre-registered
threshold. That threshold is also `[OPEN]` and must be chosen before measurement, for the same reason.

### 9A.5 The finding in one sentence

`binary32` arithmetic is not the error budget's problem — **quantisation is**, by three orders of
magnitude — and Phase 2's equivalence rules, which were written before this analysis existed, do not yet
account for it.

## 10. Unresolved questions

1. Is `-ffloat-store` sufficient to align x87 with SSE2, and what does it cost? **[OPEN]**
2. Should accumulation use pairwise summation in the output head from the start, given §9.2 shows it is
   the dominant error source? **Proposed: yes** — the head has the longest reduction and is called once
   per token, so the cost is small and the benefit is the largest error term. **[OPEN]**
3. Is a `float64` RoPE table required? **[OPEN]**
4. Does the `1e-3` token-agreement tolerance make equivalence testing meaningful, or does §9.4 imply it
   should be tighter? **Proposed: report the observed agreement rate, not just pass/fail.** **[OPEN]**
5. Should int8 weight storage arrive before or after the first full evaluation baseline? **Proposed:
   after**, so the quantisation effect is measured against a known-good reference. **[OPEN]**
6. What is the worst-case condition number `κ` on real activations (§9.7)? **Unmeasured.** **[OPEN]**
7. Does the 89× overflow headroom in §9.6 survive a trained model with larger logits, even though
   max-subtraction makes overflow impossible? **Structurally yes, empirically unverified.** **[OPEN]**
