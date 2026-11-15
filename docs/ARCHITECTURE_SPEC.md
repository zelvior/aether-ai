# AETHER — Architecture Specification

Status: **Proposal.** No part of this architecture has been implemented, trained, or measured.
Every dimension, parameter count, and budget below is a **proposed value**, not a result.

Normative: this document defines what Phase 4 will implement. Changes require a research proposal.

Related: [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) (motivation) ·
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) (arithmetic) · [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md)
(numerics) · [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) (container) ·
[`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) (vocabulary)

---

## 1. Design constraints, restated as quantities

The principles in the roadmap are qualitative. For architecture work they must become numbers.
These are the numbers this specification is written against.

| Constraint | Quantity | Source |
| --- | --- | --- |
| Address-space budget | Design against **2 GiB** user VA; target **≤ 512 MiB** runtime envelope | [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2 |
| Model parameter budget (primary) | **≤ 10 M** parameters | §5.1 |
| Model parameter budget (floor) | **≥ 1 M** parameters | §5.1 |
| Inference compute format | `binary32` | [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §3 |
| Weight storage format | `binary32` in Phase 4; int8 candidate in Phase 8 | [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §4 |
| Runtime dependencies | None beyond the C standard library | Roadmap principle 10 |
| Vector assumptions | Scalar path correct on i386 baseline; SSE2 only behind runtime dispatch | [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §3.3 |
| Training memory | Must fit 2 GiB **with** activation checkpointing | §9 |

The 10 M parameter ceiling is the binding design choice. It is chosen so that the model fits the
memory envelope with an order of magnitude of headroom, trains on CPU in a tractable time, and
remains small enough for one maintainer to reason about end to end.

---

## 2. What "from scratch" requires

AETHER may not import a pretrained checkpoint. The architecture must therefore be:

1. **Trainable from random initialisation** on a corpus AETHER has rights to use
   ([`DATA_POLICY.md`](DATA_POLICY.md)).
2. **Understood by its author at the level of individual weight matrices**, since there is no
   pretrained baseline to fall back on.
3. **Cheap enough to train more than once**, because the first training run will be wrong.

Requirement 3 favours the Nano configuration (§5.1) as the *first* trained model even though Config M
is the headline architecture: the pipeline must be proven on a model whose full training run is
affordable before a larger one is attempted.

---

## 3. Layer inventory

The architecture uses exactly six layer primitives. No others are introduced.

| # | Primitive | Purpose |
| --- | --- | --- |
| 1 | `RMSNorm` | Pre-normalisation before each sub-block |
| 2 | `Attention` (sliding-window, multi-head, RoPE) | Sequence mixing |
| 3 | `SwiGLU` (gated MLP) | Per-position transformation |
| 4 | `Residual add` | Skip connection |
| 5 | `Tied embedding` | Input embedding and output projection sharing one matrix |
| 6 | `Softmax` / `CrossEntropy` | Output distribution and loss |

The absence of a seventh is itself a design decision: every additional primitive is another thing to
implement, verify, and port to i386.

---

## 4. Mathematical structure

Notation: sequence length `T`; model width `d`; layer count `L`; head count `H`; head dimension
`d_h = d/H`; MLP inner width `d_ff`; vocabulary `V`; attention window `W`.

### 4.1 Embedding

Tokens `x_0 … x_{T-1} ∈ {0, …, V-1}` are mapped by a lookup into `E ∈ ℝ^{V×d}`:

```
h⁽⁰⁾_t = E[x_t]                      (1)
```

`E` is shared with the output projection (§4.6). No positional embedding tensor is added; position is
injected inside attention by RoPE (§4.3).

### 4.2 Block structure

For `ℓ = 1 … L`, with pre-normalisation:

```
a⁽ℓ⁾  = h⁽ℓ⁻¹⁾ + Attention(RMSNorm(h⁽ℓ⁻¹⁾))          (2)
h⁽ℓ⁾  = a⁽ℓ⁾  + SwiGLU(RMSNorm(a⁽ℓ⁾))                 (3)
```

### 4.3 Sliding-window attention with RoPE

RMSNorm `[S22]`, which removes the mean-subtraction and shift of Layer Normalization `[S21]`:

```
RMSNorm(x) = x / sqrt( (1/d)·Σ x_i² + ε ) · g         (4)
```

with learned gain `g ∈ ℝ^d` and `ε = 1e-5`. No mean subtraction, no bias, following `[S22]`. The
re-centering term is dropped; `[S22]` reports comparable quality to `[S21]` with lower runtime cost,
which matters on a target with no vector throughput to spare. **[ASSUMPTION]** that this holds at
AETHER's scale is untested.

QKV projection, with `W_qkv ∈ ℝ^{d × 3d}` and no bias:

```
[q, k, v] = RMSNorm(h) · W_qkv                         (5)
```

Rotary position embedding `[S24]` applied to `q` and `k` only, with base `Θ = 10000`:

```
θ_i = Θ^{-2i/d_h},   i = 0 … d_h/2 - 1                (6)
q'_{2i}   = q_{2i}·cos(t·θ_i) - q_{2i+1}·sin(t·θ_i)
q'_{2i+1} = q_{2i}·sin(t·θ_i) + q_{2i+1}·cos(t·θ_i)   (7)
```

Sliding-window scaled dot-product attention, for query position `t` over key positions
`s ∈ [max(0, t-W+1), t]`:

```
A_{t,s} = (q'_t · k'_s) / sqrt(d_h)                    (8)
P_{t,s} = exp(A_{t,s} - max_s A_{t,s}) / Σ_s exp(A_{t,s} - max_s A_{t,s})   (9)
out_t   = Σ_s P_{t,s} · v_s                            (10)
```

Equation (9) is the numerically stable form: the maximum is subtracted before exponentiation, which is
mandatory, not optional, because `binary32` overflows `exp` above 88.7. See
[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §5.

Output projection `W_o ∈ ℝ^{d×d}`, no bias: `Attention(h) = concat(out) · W_o`.

**Every head carries its own key and value projections.** Multi-query attention `[S32]` shares one
key/value head across all query heads, and grouped-query attention `[S33]` shares them across groups;
both exist to cut the **memory bandwidth** cost of decoding, where the KV cache dominates. AETHER does
**not** adopt either, and the reason is specific: at Config M the full KV cache for eight layers,
`T_max = 2048`, is `8 · 2 · 2048 · 256 · 4 = 33,554,432 B = 32.00 MiB`
([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.1), **32.1 %** of the 99.55 MiB inference budget — but AETHER's
scalar code is **not** bandwidth-bound, it is instruction-bound. Cutting KV bytes does not reduce the
number of multiply-accumulates, and the MAC count is what sets wall-clock time on a machine with no
memory-level parallelism to exploit.

**[OPEN]** Whether MQA/GQA would help once the decoder is profiled. `[S32]`/`[S33]` are cited for the
mechanism, not as evidence it helps here.

### 4.4 SwiGLU

Following the gated-MLP form with an SiLU gate and a `2/3` expansion factor (so that `d_ff` carries
the same parameter count as a `4×` ReLU MLP):

```
[gate, up] = RMSNorm(a) · W_gate_up     (W_gate_up ∈ ℝ^{d × 2d_ff})    (11)
SwiGLU(a)  = ( SiLU(gate) ⊙ up ) · W_down    (W_down ∈ ℝ^{d_ff × d})  (12)
SiLU(x)    = x · σ(x)                                                   (13)
```

`σ` is computed with a `binary32`-safe form (§[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §5.2).

**[PROPOSED]** SwiGLU rather than GELU `[S23]` or ReLU, because it is the current default in
small-model work and the extra parameters per layer are accounted for in §5. **[ASSUMPTION]** that
this holds at 1–10 M parameters is untested; it is an ablation candidate
([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §6).

### 4.7 Normalisation

AETHER uses RMSNorm `[S22]` at both pre-norm positions (equations 2 and 3 in §4.2), and at the final
output. It is the only normalisation in the model.

```
RMSNorm(x) = (x / sqrt( mean(x²) + ε )) ⊙ γ        ε = 1e-5,  γ initialised to 1
```

| Property | RMSNorm `[S22]` | LayerNorm `[S21]` |
| --- | --- | --- |
| Mean subtraction | **No** | Yes |
| Shift (β) | **No** | Yes |
| Reductions per norm | **1** (sum of squares) | 2 (mean, then variance) |
| Gain parameters | `d` | `2d` (γ and β) |

**Why the saving is real and where it shows up.** Dropping mean subtraction removes one full reduction
over `d` elements per normalisation, and dropping `β` removes `d` parameters per norm site. At Config M
that is `2·L·d + d = 4 352` gain parameters total — small in the parameter budget (0.05 %), but the
*reduction* saving is per-token and therefore matters on every forward pass.

**[PROPOSED]** `ε = 1e-5`. It only matters when a residual branch is near zero; it prevents a division by
a vanishing denominator. The value is conventional and untuned — `[OPEN]`.

**Residual connections** `[S40]` carry the unnormalised stream, and the pre-norm ordering `[S27]` is what
makes that stream's variance grow linearly rather than exponentially with depth. `[S40]` is cited for the
identity-mapping argument that motivates this: a branch whose output can be zero still passes the input
through unchanged, so depth does not require each layer to learn a perturbation from an arbitrary
baseline. `[S40]` is an **image classification** result; AETHER cites it for the mechanism, not as
evidence about language-model depth.

**Numerically, RMSNorm is what makes §9's error analysis tractable.** Its output has unit RMS by
construction, so every downstream reduction has bounded input magnitude and the condition number in
[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9.3 stays near 1 rather than growing with depth. An
un-normalised residual stream would make that analysis meaningless.

### 4.5 Final norm and output

```
h_final = RMSNorm(h⁽ᴸ⁾)                                (14)
logits  = h_final · Eᵀ          (tied to §4.1)         (15)
```

Tying `E` saves `V·d` parameters — 2 097 152 parameters at `V=8192, d=256`, i.e. **25 % of the model**
— at the cost of coupling input and output geometry. That coupling is accepted.

### 4.6 Loss

Token-level cross-entropy with label smoothing `α = 0.0` by default:

```
L = -(1/T) Σ_t log softmax(logits_t)[y_t]              (16)
```

`log_softmax` is computed with the max-subtraction trick (§[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §5.3).

---

## 5. Proposed configurations

Both configurations are **proposed values**. Parameter counts are derived from the formulas in §6 with
the arithmetic shown, and were computed programmatically rather than estimated. They are not measured
from an implementation.

### 5.1 Primary architecture: AETHER-M (Config M)

| Symbol | Value | Note |
| --- | --- | --- |
| `V` | 8192 | Proposed vocabulary ([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §2) |
| `d` | 256 | Model width |
| `L` | 8 | Layers |
| `H` | 8 | Heads |
| `d_h` | 32 | `d/H` |
| `d_ff` | 688 | SwiGLU inner width; see §5.3 |
| `W` | 256 | Attention window (tokens) |
| `T_train` | 512 | Training context |
| `T_max` | 2048 | Maximum context the format allows |
| `Θ` | 10000 | RoPE base |
| `ε` | 1e-5 | RMSNorm epsilon |
| **Parameters** | **8 425 728** | §6.1 |

### 5.2 Floor architecture: AETHER-N (Config N)

The first model to be trained, because its full training run is affordable and its failure modes are
legible.

| Symbol | Value | Note |
| --- | --- | --- |
| `V` | 8192 | Proposed vocabulary |
| `d` | 128 | Model width |
| `L` | 4 | Layers |
| `H` | 4 | Heads |
| `d_h` | 32 | `d/H` |
| `d_ff` | 344 | SwiGLU inner width; see §5.3 |
| `W` | 128 | Attention window (tokens) |
| `T_train` | 256 | Training context |
| `T_max` | 512 | Maximum context the format allows |
| `Θ` | 10000 | RoPE base |
| `ε` | 1e-5 | RMSNorm epsilon |
| **Parameters** | **1 840 256** | §6.2 |

Config N is not a toy for its own sake. Its purpose is to exercise the whole pipeline — tokenizer,
training, format, runtime, evaluation — on something whose entire lifecycle fits in a day of CPU time.
Only when that works does Config M get trained.

### 5.3 A note on `d_ff`

A conventional `4×` ReLU MLP has two matrices of `d × 4d`, i.e. **`8d²` parameters**. A SwiGLU block
(§4.4) has:

- `W_gate_up`: `d × 2·d_ff` → `2·d·d_ff` parameters
- `W_down`: `d_ff × d` → `d·d_ff` parameters
- **total: `3·d·d_ff`** — note the factor of **3**, not 2

Setting `3·d·d_ff = 8d²` gives `d_ff = 8d/3 ≈ 2.667d`. AETHER rounds to the nearest multiple of 8:

| Config | `d` | Exact `8d/3` | Chosen `d_ff` | MLP params | vs `8d²` |
| --- | --- | --- | --- | --- | --- |
| Config M | 256 | 682.7 | **688** | 528 384 | 1.008× |
| Config N | 128 | 341.3 | **344** | 132 096 | 1.008× |
| Config T | 64 | 170.7 | **168** | 64 512 | 0.984× |

So `d_ff = 2.688d` rather than the `4d` a ReLU MLP would use, because the extra gate matrix is paid
for out of the inner width. **An earlier draft of this document used `d_ff = 1024` with an incorrect
`2·d·d_ff` parameter formula; both were wrong, and the correction raised the true parameter count by
about 25 %.** The figures in this document are the corrected ones.

Why 688 and not 672 (`2.625d`) or 704 (`2.75d`): the factor was set to match `8d²` as closely as an
integer multiple of 8 permits, so that §10's comparison against a plain Transformer is on equal
parameter footing. **[PROPOSED]** and freely changeable — `d_ff` is a format field.

### 5.3B Deriving the window from the cost model

`W` governs three quantities that trade against each other. Holding all of Config M's dimensions fixed
except `W`, and evaluating at the **maximum context** `T = T_max = 2048` (the worst case for the score
buffer and KV cache):

```
compute(W)  = L·(4d² + 2·d·N(T,W) + 3·d·d_ff) + T·d·V     MACs,  N(T,W) = Σ_{t<T} min(t+1, W)
score_mem(W) = H · W · T · 4                              bytes, one layer's prefill scores
kv_mem(W)    = 2 · L · W · d · 4                          bytes, ring-buffer retention
```

Computed with `tools/phase2_calc.py`:

| `W` | Prefill MACs at `T=2048` | vs. `W = T` | Score buffer | KV ring |
| --- | --- | --- | --- | --- |
| 64 | 14 889 910 272 | −35.1 % | 4.00 MiB | 1.00 MiB |
| 128 | 15 401 746 432 | −32.9 % | 8.00 MiB | 2.00 MiB |
| **256** | **16 375 087 104** | **−28.7 %** | **16.00 MiB** | **4.00 MiB** |
| 512 | 18 120 441 856 | −21.1 % | 32.00 MiB | 8.00 MiB |
| 1024 | 20 805 844 992 | −9.4 % | 64.00 MiB | 16.00 MiB |
| 2048 | 22 955 425 792 | — | 128.00 MiB | 32.00 MiB |

### The trade, stated as elasticities

Moving from `W = 256` to `W = 512` costs **+10.7 %** prefill work and **+16 MiB** of score buffer, and
buys nothing at all: `RF(8, 256) = 2041` already spans `T_max = 2048` (§5.3A). Moving from 256 down to
128 halves the score buffer and saves **6.3 %** prefill, but drops coverage to 509 tokens — a 75 %
context loss for a 6 % compute saving.

**Those two numbers, side by side, are the entire window decision.** Compute is nearly insensitive to
`W`; coverage is extremely sensitive to it. A design that optimised FLOPs alone would pick `W = 64` and
silently throw away three quarters of its context. The receptive-field invariant is what prevents that,
and it is why §5.3A exists before this section rather than after it.

### Why the curve is so flat

At `T = 2048` and `d = 256`, the attention-score term `2·d·N(T,W)` is small relative to the projection
terms `4d²` per token. For `W = 256`, attention contributes **67.11 M of 672.2 M** context-relevant MACs
— about 10 %. This is the quantitative form of §7.3's finding: **AETHER's prefill is dominated by
projections and the SwiGLU block, not by attention.** Window choice is therefore a *memory and
capability* decision, not a compute decision.

**[PROPOSED, NOT MEASURED]** All figures above are analytic. No kernel has been written and no timing
has been taken; the real cost curve will include constant factors these formulas omit.

### 5.3A The receptive-field invariant

A sliding-window causal attention layer reaches back `W` tokens. Each additional layer extends that
reach by `W − 1` — one newly attended position, whose own window is already available. The whole stack
therefore reaches:

```
RF(L, W) = L · (W − 1) + 1        tokens
```

**Any configuration whose `RF < T_max` declares a context it cannot use.** The model would accept
`T_max` tokens and attend to only the most recent `RF` of them; the rest would be silently inert —
costing KV-cache memory, prefill FLOPs and latency while contributing nothing.

Inverting the relation gives the minimum admissible window for a declared context:

```
W_min = ceil( (T_max − 1) / L ) + 1
```

Applied to every AETHER configuration:

| Config | `L` | `W` | `RF` | `T_max` | Coverage | `W_min` |
| --- | --- | --- | --- | --- | --- | --- |
| Config M | 8 | 256 | 2 041 | 2 048 | **99.7 %** | 257 |
| Config N | 4 | 128 | 509 | 512 | **99.4 %** | 129 |
| Config T | 2 | 128 | 255 | 256 | **99.6 %** | 129 |

**This invariant caught a real defect during Phase 2.** Config T was originally proposed with `W = 64`,
giving `RF = 2·63 + 1 = 127` against a declared `T_max = 256` — **49.6 % coverage**. The fixture would
have validated a pipeline while half its declared context was unreachable, and nothing in the memory or
parameter arithmetic would have revealed it: every byte and parameter count was correct. The bug was
invisible to every check in this document except this one.

The fix was `W = 128`, with **zero parameter cost** — `W` is not a parameter, only a compute and
memory determinant.

#### Why the designs sit at 99.4–99.7 % and not 100 %

Because `W` is rounded to powers of two for cache-line and kernel-shape reasons, and `W_min` is one more
than the power of two in each case (257, 129, 129). Choosing `W = 257` would give exact coverage at the
cost of an awkward, non-power-of-two inner dimension in the attention mask.

**[PROPOSED]** The 0.3–0.6 % shortfall is accepted. The last few tokens of the declared maximum context
are unreachable from the final layer, which is a real but bounded limitation, and it is **documented
rather than hidden**.

#### The general lesson

Three independent arithmetic invariants govern these configurations, and only one was checked by
default:

| Invariant | Form | Was it obvious? |
| --- | --- | --- |
| Parameter accounting | `4d² + 3·d·d_ff + 2d` per layer | Yes — it is what the tables compute |
| Memory fit | peak ≤ envelope | Yes — `MEMORY_BUDGET.md` §5 |
| **Receptive field** | `L·(W−1)+1 ≥ T_max` | **No — it was missed** |

`tools/phase2_calc.py` now asserts the third one mechanically, so a future change to `W`, `L` or `T_max`
cannot reintroduce the defect silently.

### 5.4 Pipeline-validation configuration: AETHER-T (Config T)

Between "nothing" and Config N there is a step worth naming. Config T is deliberately too small to be
useful as a language model, which is exactly its purpose: it is a **test fixture** that exercises the
entire pipeline — tokenizer, training loop, checkpoint writing, AMC serialisation, runtime loading,
forward pass, evaluation harness — fast enough to run repeatedly and cheap enough to train **on the
32-bit target itself**.

| Symbol | Value |
| --- | --- |
| `V` | 2048 |
| `d` | 64 |
| `L` | 2 |
| `H` | 2 |
| `d_h` | 32 |
| `d_ff` | 168 |
| `W` | 128 |
| `T_train` | 128 |
| `T_max` | 256 |
| **Parameters** | **228 672** |

Component split: embeddings 131 072 (57.3 %), attention 32 768 (14.3 %), MLP 64 512 (28.2 %),
norm gains 320 (0.14 %).

**Config T must never be described as "AETHER's model", benchmarked, or cited as evidence of
capability.** It has one job: prove the pipeline is not broken before anything expensive is attempted.
Its training cost is derived in [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §6.2.

**[PROPOSED], not measured.** No Config T run has occurred.

## 6. Parameter accounting

Parameters, excluding activation memory:

```
P = V·d                      (tied embedding)
  + L · [ 3d²  + d² ]        (attention: W_qkv, W_o)
  + L · [ 3·d·d_ff ]         (SwiGLU: W_gate_up d×2d_ff, W_down d_ff×d)
  + L · [ 2d ]               (2 RMSNorm gains per layer)
  + d                        (final RMSNorm gain)
```

Note the deliberate absence of bias vectors. Every linear layer is bias-free. This is not stylistic:
it removes `3d + d + 2d_ff` parameters per layer and, more importantly, removes a class of
shape/format edge cases in the loader.

### 6.1 Config M worked arithmetic

| Component | Expression | Value |
| --- | --- | --- |
| Tied embedding | `8192 × 256` | 2 097 152 |
| Attention per layer | `3(256²) + 256² = 4 × 65 536` | 262 144 |
| SwiGLU per layer | `3 × 256 × 688 = 2(256×688) + (688×256)` | 528 384 |
| Norms per layer | `2 × 256` | 512 |
| **Per layer** | `262 144 + 528 384 + 512` | **791 040** |
| All layers | `8 × 791 040` | 6 328 320 |
| Final norm | `256` | 256 |
| **Total** | `2 097 152 + 6 328 320 + 256` | **8 425 728** |

Composition: embedding **24.9 %**, attention **24.9 %**, MLP **50.2 %** (norms 0.05 %). The MLP
dominates, which is expected for a SwiGLU block and means **MLP quantisation is where Phase 8 should
look first** — it is half the model.

### 6.2 Config N worked arithmetic

| Component | Expression | Value |
| --- | --- | --- |
| Tied embedding | `8192 × 128` | 1 048 576 |
| Attention per layer | `4 × 128²` | 65 536 |
| SwiGLU per layer | `3 × 128 × 344` | 132 096 |
| Norms per layer | `2 × 128` | 256 |
| **Per layer** | `65 536 + 132 096 + 256` | **197 888** |
| All layers | `4 × 197 888` | 791 552 |
| Final norm | `128` | 128 |
| **Total** | `1 048 576 + 791 552 + 128` | **1 840 256** |

Composition: embedding **57.0 %**, attention **14.2 %**, MLP **28.7 %**. At this size the embedding
dominates, which is the opposite of Config M and is itself a finding: **vocabulary choice is a
first-order design decision at the small end.**

## 7. Compute accounting

MACs, not FLOPs, throughout; FLOPs are `2 × MACs` for multiply-and-accumulate. These are
**analytical counts**, computed from the formulas, not benchmarks. They bound work; they say nothing
about speed.

### 7.1 Prefill (processing `T` tokens)

Per layer:

| Component | MACs |
| --- | --- |
| QKV projection | `3Td²` |
| Attention scores (causal, `W`-window) | `N(T,W) · d` |
| Value mixing | `N(T,W) · d` |
| Output projection | `Td²` |
| SwiGLU | `2T·d·d_ff` |

where `N(T,W)` is the **exact** number of causal attended pairs,
`N(T,W) = Σ_{t=0}^{T-1} min(t+1, W)`. Using `T·W·d` as an approximation **overstates** windowed
attention cost whenever `T < 2W`, because early positions cannot attend to a full window. All figures
below use the exact count.

Note that SwiGLU *MACs* are `3·T·d·d_ff` and its *parameters* are `3·d·d_ff` (§6). Three matrices, each
the gate matrix produces twice its input width in a single multiply. Parameters and MACs differ by
`3/2` here, which is a common source of confusion between the two accountings.

Plus the output head, `T·d·V`, once.

**Config M at `T = 512`, `W = 256`, exact pair count `N(512,256) = 98 432`:**

| Component | MACs |
| --- | --- |
| QKV | 100 663 296 |
| Scores + mixing (`2 · 98 432 · 256`) | 50 397 184 |
| Output projection | 33 554 432 |
| SwiGLU (`2 · 512 · 256 · 688`) | 180 355 072 |
| Per layer | 364 969 984 |
| All 8 layers | 2 919 759 872 |
| Output head (`512 · 256 · 8192`) | 1 073 741 824 |
| **Total** | **3 993 501 696 MACs ≈ 7.99 GFLOP** |

Full-causal attention at `T = 512` costs 4 128 243 712 MACs (8.26 GFLOP). **At the training length the
window saves only 3.3 % of total prefill compute** — the output head and MLP dominate. This is stated
plainly because it would be easy, and misleading, to claim the window is a large prefill win at
`T = 512`. It is not.

**Where the window actually pays**: at inference-time context.

| `T` | Attention term, windowed | Attention term, full-causal | Reduction in attention term |
| --- | --- | --- | --- |
| 256 | 16 842 752 | 16 842 752 | 0.0 % (window ≥ `T`) |
| 512 | 50 397 184 | 67 239 936 | 25.0 % |
| 1024 | 117 506 048 | 268 697 600 | 56.3 % |
| 2048 | 251 723 776 | 1 074 266 112 | 76.6 % |
| 4096 | 520 159 232 | 4 296 015 872 | 87.9 % |

The window's primary benefit is **memory and decode cost**, not prefill FLOPs (§7.2, §10.1).

### 7.2 Decode (one token)

Per layer: `3d²` (QKV) + `2·W·d` (windowed attention) + `d²` (output) + `3·d·d_ff` (SwiGLU).
Plus `d·V` for the head.

**Config M at `W = 256`, `d_ff = 688`:**

| Component | MACs per token |
| --- | --- |
| QKV | 196 608 |
| Attention over window (`2 · 256 · 256`) | 131 072 |
| Output projection | 65 536 |
| SwiGLU (`2 · 256 · 688`) | 352 256 |
| Per layer | 745 472 |
| All 8 layers | 5 963 776 |
| Output head | 2 097 152 |
| **Total** | **9 469 952 MACs ≈ 18.94 MFLOP/token** |

**Config N:** `4 × 186 368 + 1 048 576 = 1 794 048` MACs ≈ 3.59 MFLOP/token.

The window makes decode cost **independent of context length**: `2·W·d` does not contain `T`. This is
the property that lets the model run in bounded time at any context up to `T_max`.

### 7.3 What these numbers do not tell you

Tokens per second **cannot be derived from MACs alone.** It depends on memory bandwidth, cache
behaviour, instruction throughput, and the runtime's implementation quality — none of which exist yet.
**[OPEN]** No tokens-per-second figure is stated anywhere in this repository, and none should be until
Phase 9 measures one ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §3).

---

## 8. Scope of capability claims

**AETHER does not claim, and must not claim, that this architecture produces a general-purpose
language model.**

What Config M is plausibly sized for, based on `[S10]`'s finding that narrow data plus small models can
produce coherent output within a restricted domain:

- A **narrow-domain** text model over a corpus of AETHER's own choosing and rights.
- **Short-context** completion, `T ≤ 512` tokens of training context.
- Demonstration that the **pipeline** end to end produces a model that generates *something*
  syntactically coherent within its domain.

What it is **not** sized for, and what no AETHER document may imply:

- General-purpose instruction following.
- Factual reliability of any kind.
- Multi-turn dialogue competence.
- Any benchmark comparison against a published model.
- Reasoning, coding, mathematics, or multilingual capability.

This section is normative. Any model card produced from this architecture must restate these limits
using [`MODEL_CARD_TEMPLATE.md`](MODEL_CARD_TEMPLATE.md) §7–8.

---

## 8A. Initialisation and optimisation

Phase 2 originally specified the forward pass and nothing about how the parameters come to exist. That
is a gap: an architecture without an initialisation and optimiser schedule is not trainable, and the
values chosen affect stability at least as much as the layer shapes.

All values below are **[PROPOSED]**. None has been validated by a training run.

### 8A.1 Weight initialisation

| Tensor | Distribution | Rationale |
| --- | --- | --- |
| `tok.embed` | `N(0, 1/d)` | Keeps embedding rows unit-scale going into RMSNorm |
| `attn.wqkv` | `N(0, 1/d)` | Preserves variance through the projection |
| `attn.wo` | `N(0, 1/d)` | Symmetric with the input projection |
| `mlp.wgateup` | `N(0, 1/d)` | Same convention; the gate half is additionally initialised smaller by √2 to offset SiLU's damping near zero |
| `mlp.wdown` | `N(0, 1/(3·d_ff))` | Compensates for the wider input, keeping output variance unit-scale |
| All RMSNorm gains | `1.0` | Identity at initialisation, as in `[S22]` |
| All biases | — | None exist (§6) |

The `wdown` scaling matters: its input has `3·d_ff` effective contributions from a gated product, so an
unscaled `1/d` initialisation would roughly triple output variance per layer. With `L = 8` that
compounds to a factor of about 6.5 in standard deviation across the network, which is enough to make
early training unstable.

**[ASSUMPTION]** That `N(0, 1/d)` is appropriate here. It is the convention behind the `1/√d_h`
scaling trick in `[S1]`, and §[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9.6 shows it yields
`O(1)` attention logits at initialisation for these dimensions. That is a consistency check, not
evidence that it trains well.

**[OPEN]** Whether residual-branch output scaling (`1/√(2L)` on `wo` and `wdown`, a common
deep-Transformer practice) is needed at `L = 8` is untested. At this depth it is probably unnecessary,
but "probably" is doing work here.

### 8A.2 Normalisation placement

Pre-norm (`x + f(RMSNorm(x))`), per `[S21]`-era convention and `[S27]`.

`[S27]` shows theoretically and empirically that **post-norm** Transformers require learning-rate
warm-up because their gradient magnitude at initialisation is independent of depth and therefore large,
while **pre-norm** gradients decay with depth and train stably from a large learning rate immediately.
AETHER uses pre-norm because it removes the need for warm-up, which on a machine where every epoch costs
hours is a real saving.

**[ESTABLISHED]** The gradient-scaling result is from `[S27]`.
**[ASSUMPTION]** That the result holds at `d=256, L=8`, well outside the scale studied there.

### 8A.3 Optimiser

AdamW `[S28]` — Adam with **decoupled** weight decay.

`[S28]` establishes that L2 regularisation and weight decay are *not* equivalent for adaptive methods,
and that decoupling the decay from the gradient-based update improves generalisation. Since AETHER uses
Adam-family updates, this is not a stylistic choice: the coupled form would apply decay through the
second-moment estimate and produce a different, unintended effective schedule.

| Hyperparameter | Proposed value | Note |
| --- | --- | --- |
| `β₁`, `β₂` | 0.9, 0.95 | `β₂` lower than the 0.999 default; standard for language models |
| `ε` | 1e-8 | Optimiser epsilon, distinct from the RMSNorm epsilon |
| Weight decay | 0.1, applied to weight matrices only | **Not** to RMSNorm gains or embeddings |
| Gradient clipping | global norm 1.0 | Cheap insurance against a single bad batch |
| Learning rate | 3e-4 peak, cosine decay to 10 % of peak | **[OPEN]** — untuned |
| Warm-up | none | Justified by pre-norm (§8A.2) |
| Precision | `binary32` weights, gradients, and both moments | §[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6.1 |
| Batch | micro-batch 4–8, gradient accumulation to an effective 32–64 | §[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6.3 |

Excluding RMSNorm gains from weight decay is not cosmetic: decaying a normalisation gain toward zero
directly attenuates the signal that normalization is meant to preserve.

**[OPEN]** The learning rate is a guess, and the transfer plan was unjustified. AETHER cannot afford a sweep
at Config M scale ([`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §7), so the plan was to tune on
Config T and transfer to Config M.

**That transfer is biased.** Under the standard parameterisation the update magnitude scales as `√(width)`, so
a learning rate optimal at `d = 64` is systematically **too large** at `d = 256` — by roughly `√4 = 2×` in the
projection layers. The derivation is in [`OPTIMISATION_THEORY.md`](OPTIMISATION_THEORY.md) §2.

The Maximal Update Parameterisation (μP) `[S50]` is the standard remedy: it reparameterises the model so that
optimal hyperparameters are stable across width, making transfer justified by construction rather than assumed.
AETHER has **not** adopted μP — it has not been validated at widths as small as AETHER's, and it conflicts with
`[S1]`'s `1/√d_h` attention scaling ([`OPTIMISATION_THEORY.md`](OPTIMISATION_THEORY.md) §3.3).

**This is now an explicit open decision rather than a silent assumption.** The cheap resolution costs 7.5 hours
of Config N training (`OPTIMISATION_THEORY.md` §4.1) and should be run before any Config M training is
attempted. Whatever is decided must be recorded in the model card as **untuned**.

### 8A.4 Loss and sampling

Cross-entropy with label smoothing `α = 0` (§4.6). Sampling is not part of the architecture; the
runtime will support greedy and temperature sampling, with the evaluation plan mandating greedy for
equivalence testing ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §5.1).

### 8A.5 Dropout

**[PROPOSED]** No dropout. At 10 tokens/parameter the model is not in a regime where over-fitting is the
first-order problem, and dropout adds a nondeterminism source that complicates equivalence testing
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §7.1). If Phase 9 shows over-fitting, this is
revisited with evidence.

## 9. Training implications discovered in this phase

The training-memory arithmetic ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6) produces a requirement that
changes Phase 5's design, and is recorded here because it constrains the architecture:

| Micro-batch | Activation memory | Total training memory |
| --- | --- | --- |
| 1 | 181.50 MiB | 310.07 MiB |
| 2 | 363.00 MiB | 491.57 MiB |
| 4 | 726.00 MiB | 854.57 MiB |
| 8 | 1452.00 MiB | **1580.57 MiB** |

With activation checkpointing (storing one layer's activations and recomputing the rest):

| Micro-batch | Activation memory | Total |
| --- | --- | --- |
| 4 | 90.75 MiB | 219.32 MiB |
| 8 | 181.50 MiB | **310.07 MiB** |
| 16 | 363.00 MiB | 491.57 MiB |

**Consequence:** the training implementation **must** support activation checkpointing from its first
version. This is not an optimisation to add later; without it, Config M cannot be trained inside a
conservative 32-bit budget at any useful micro-batch. The cost is one additional forward pass per
step — roughly a 33 % increase in training compute — which is accepted.

**[OPEN]** Whether gradient accumulation across micro-batches of 2–4 reaches an equivalent effective
batch to a micro-batch of 8 is scale-dependent and must be measured, not assumed.

---

## 10. Alternatives considered and rejected

Two alternatives were specified in enough detail to compare. Both are rejected **for Phase 4**, not
ruled out permanently.

### 10.1 Alternative A — Full-attention Transformer, no window

The conventional decoder-only baseline.

| Property | Config M windowed | Alternative A (full attention) |
| --- | --- | --- |
| Parameters | 8 425 728 | 8 425 728 (identical) |
| Prefill MACs at `T=512` | 3.99 G | 4.13 G (+3.3 %) |
| Decode MACs/token at `t=512` | 8.06 M | 9.11 M (+13.0 %) |
| Score buffer at `T=512` | 4.00 MiB | 8.00 MiB |
| Score buffer at `T=2048` | **16.00 MiB** | **128.00 MiB** (8.0×) |
| Attention-term MACs at `T=2048` | 251.7 M | 1 074.3 M (4.3×) |
| Receptive field | 256 tokens/layer | Unbounded |
| Implementation complexity | Low | Low |

**Why rejected:** at `T = 512` — the training length — the two differ by only 3.3 % of prefill compute,
which is instructive in itself. The separation appears at *inference* context: at `T = 2048` the
window is 8.0× smaller in transient memory and 4.3× cheaper in the attention term. The decision is
therefore about **what the architecture is allowed to do later**, not about training cost. Full
attention at `T = 2048` costs 128 MiB of transient buffer for a single layer's score matrix — 6.25 %
of the entire 2 GiB budget for one temporary allocation — which makes the 32-bit story fragile for a
capability an 8 M parameter model cannot exploit anyway.

**What is lost:** unbounded receptive field. This is a real capability loss, not a free win.

**Revisit condition:** if Phase 9 shows windowed attention materially limits quality on a task AETHER
actually cares about, Alternative A is reconsidered with an explicit memory-cost argument.

### 10.2 Alternative B — Hybrid: alternating gated-recurrence and windowed-attention layers

Following `[S7]`'s alternating structure, replacing every other attention block with a gated linear
recurrence.

| Property | Config M | Alternative B (hybrid, 4+4) |
| --- | --- | --- |
| Parameters | 8 425 728 | ~9.1 M (recurrent block adds ~1.0–1.5 d² per layer) |
| Prefill compute | `O(T·W·d)` per layer | `O(T·d²)` chunked for recurrence |
| Decode compute/token | `O(W·d)` | `O(d²)` |
| Decode state memory | KV cache `2·W·d` per layer | `O(d)` per layer — **smaller** |
| Implementation complexity | Low | **High** (second primitive, chunked training form) |
| Verification difficulty | Low (compare against dense attention) | **High** (no simple reference) |
| Numerical risk | Moderate | **Higher** (state decay in `binary32`) |

**Why rejected for Phase 4:** Alternative B requires a second, harder sequence-mixing primitive whose
correctness is difficult to verify independently, in a project with no existing test corpus and one
maintainer. Its advantages — smaller decode state and constant-time decode — matter most at large
batch and long context, neither of which is AETHER's situation at 8 M parameters.

**Why it is not dismissed:** the state-memory advantage is real and directly relevant to the 32-bit
budget. This is the most likely Phase 8 direction.

**Revisit condition:** Phase 8, after a windowed baseline exists and can be compared against something
honest.

---

## 11. Implementation risks

| # | Risk | Severity | Mitigation |
| --- | --- | --- | --- |
| R1 | Numerical drift between scalar and vector paths produces silently different outputs | High | Equivalence tests against the scalar path for every vector kernel; tolerance stated, not assumed ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §6) |
| R2 | x87 extended-precision double rounding makes the 32-bit build's outputs differ from 64-bit | High | Explicit `FLT_EVAL_METHOD` policy; comparison protocol in [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §5 |
| R3 | Window size `W=256` is chosen without evidence and is wrong | Medium | `W` is a format-field, not a compile-time constant; sweep is a Phase 8 ablation |
| R4 | Tied embedding hurts quality more at 8 M parameters than at large scale | Medium | Untie is a single-line change; ablation available |
| R5 | SwiGLU's extra parameters are not worth it at this scale | Medium | GELU-MLP ablation ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §6) |
| R6 | Training at Nano config is too slow to iterate | Medium | Nano is sized precisely to make this measurable early |
| R7 | Softmax overflow at high logit magnitudes even with max-subtraction order effects | Low | Max-subtraction is mandatory; overflow guard in `exp` ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §5.1) |
| R8 | Attention window interacts badly with RoPE at boundaries | Medium | Window boundaries are absolute positions; test at window edge explicitly |
| R9 | Model does not learn anything at all at this scale | Medium | Nano-first strategy surfaces this cheaply |

None of these risks is mitigated by argument. Each requires an experiment that does not yet exist.

---

## 12. Unresolved questions

1. **Is 8.43 M parameters enough to learn anything measurable** on a plausible corpus? **[OPEN]**
2. **Is `W = 256` adequate**, or does capability collapse without long-range mixing? **[OPEN]**
3. **Should the embedding be untied** at this scale? **[OPEN]**
4. **SwiGLU vs GELU-MLP** at 1–10 M parameters — no evidence either way. **[OPEN]**
5. **Effective batch size vs micro-batch + accumulation** under checkpointing. **[OPEN]**
6. **Does `binary32` suffice for the recurrence-free design**, or does attention logit growth at
   `T = 2048` force a scaling strategy (e.g. `1/sqrt(d_h)` becomes inadequate)? **[OPEN]**

---

## 13. Status summary

| Item | Status |
| --- | --- |
| Architecture selected | **Proposed** — Config M primary, Config N first |
| Parameter counts | **Derived analytically** (§6), not measured |
| Compute counts | **Derived analytically** (§7), not benchmarked |
| Alternatives evaluated | 2, rejected with stated revisit conditions |
| Implemented | **Nothing** |
| Trained | **Nothing** |
| Measured | **Nothing** |
| 32-bit compatibility | **Untested. No claim is made.** |

Phase 4 may begin implementing this specification. Phase 4 does not begin in this phase.
