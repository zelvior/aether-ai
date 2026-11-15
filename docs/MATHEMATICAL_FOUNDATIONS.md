# AETHER — Mathematical Foundations

Status: **Derivation.** Everything here is algebra, calculus, and counting. **No measurement exists**; figures
are exact given the stated assumptions, and every assumption is named.

This document fills a real gap: Phase 2 specified *what* AETHER computes and *how much* it costs, but never
derived *why* the costs have the coefficients they have, and never wrote down the backward pass at all. Both
are prerequisites for implementing anything correctly.

Related: [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) (the forward pass) ·
[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) (precision) ·
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) (where `6ND` is used) ·
[`OPTIMISATION_THEORY.md`](OPTIMISATION_THEORY.md) (μP and hyperparameter transfer)

---

## 1. Notation

| Symbol | Meaning |
| --- | --- |
| `d` | Model width (embedding dimension) |
| `d_ff` | SwiGLU inner width |
| `L` | Number of layers |
| `H` | Number of attention heads |
| `d_h` | Head dimension, `d_h = d / H` |
| `V` | Vocabulary size |
| `T` | Sequence length |
| `W` | Attention window |
| `b` | Batch size |
| `θ` | All parameters, `N = |θ|` |
| `⊙` | Elementwise product |
| `σ` | Logistic sigmoid, `σ(x) = 1/(1+e^{-x})` |

**Convention on FLOPs.** A multiply-accumulate (MAC) is counted as **2 FLOPs** — one multiply, one add. Every
figure in AETHER's documentation follows this, and AETHER's own tables use MACs while the literature uses
FLOPs. **A factor-of-2 discrepancy between an AETHER table and a paper is almost certainly this convention,
not an error.**

---

## 2. Why the parameter count is what it is

Per layer, four parameter tensors:

| Tensor | Shape | Parameters |
| --- | --- | --- |
| `W_qkv` | `d × 3d` | `3d²` |
| `W_o` | `d × d` | `d²` |
| `W_gate_up` | `d × 2·d_ff` | `2·d·d_ff` |
| `W_down` | `d_ff × d` | `d·d_ff` |
| RMSNorm gains (2 sites) | `d` each | `2d` |

```
P_layer = 3d² + d² + 2·d·d_ff + d·d_ff + 2d
        = 4d² + 3·d·d_ff + 2d
```

**The SwiGLU coefficient is 3, not 2.** This is the single most-often-miscounted term in the architecture, because
`W_gate_up` produces `2·d_ff` outputs (gate and up projections stacked) while `W_down` consumes `d_ff`.
Together: `2·d·d_ff + 1·d·d_ff = 3·d·d_ff`.

Total:

```
N = V·d  +  L·(4d² + 3·d·d_ff + 2d)  +  d
    └──┘     └──────────────────┘      └┘
   embedding      per-layer body      final norm
```

### 2.1 Verified against every AETHER configuration

| Config | `V` | `d` | `L` | `d_ff` | Embedding | Body | Final | **Total** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T | 2048 | 64 | 2 | 168 | 131,072 | 97,280 | 64 | **228,672** |
| N | 8192 | 128 | 4 | 344 | 1,048,576 | 791,040 | 128 | **1,840,256** |
| M | 8192 | 256 | 8 | 688 | 2,097,152 | 6,328,256 | 256 | **8,425,728** |

All three checked by `tools/phase2_calc.py`, which is the single source of truth for these numbers.

---

## 3. The SwiGLU width rule

A 4× dense ReLU MLP has two matrices of `d × 4d`, i.e. **`8d²`** parameters. SwiGLU has `3·d·d_ff`. Equating:

```
3·d·d_ff = 8d²   ⇒   d_ff = 8d/3 ≈ 2.667d
```

AETHER rounds `d_ff` to a multiple of 8:

| Config | `8d/3` | Chosen | Parity `3·d·d_ff / 8d²` |
| --- | --- | --- | --- |
| M | 682.67 | 688 | 1.0078 |
| N | 341.33 | 344 | 1.0078 |
| T | 170.67 | 168 | 0.9844 |

**Why match `8d²` at all?** So that comparisons against a plain Transformer are on equal parameter footing.
Without this, an ablation of "SwiGLU vs ReLU" would confound activation choice with parameter count.

### 3.1 The compute consequence

Parameters and compute coincide here, which is worth stating because the opposite is often assumed:

| Quantity | Coefficient |
| --- | --- |
| SwiGLU parameters | `3·d·d_ff` |
| SwiGLU **MACs per token** | `3·d·d_ff` |

**The ratio is 1:1.** Each of the three matrices — gate, up, down — is `d × d_ff` and is applied once per
token, so parameters and MACs coincide exactly.

> **Correction, recorded deliberately.** Earlier revisions of this document and of
> [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §7 claimed SwiGLU MACs were `2·d·d_ff`, giving a "3:2"
> parameter-to-compute ratio, and declared that "parameter counting overstates SwiGLU's compute by 50 %".
> **That was wrong.** The error was treating the `d × 2·d_ff` fused gate/up weight as one matrix applied
> once. Fusing the weights does not fuse the arithmetic: gate and up are two independent projections that
> each consume `d·d_ff` MACs, and the down projection consumes a third. Charging two undercounted every
> compute figure in the project by **28.7 %**. `tools/phase2_calc.py` now charges `3·d·d_ff` and asserts the
> 2× backward identity, which is what caught it.

---

## 4. Forward pass, fully derived

### 4.1 Block structure

```
a⁽¹⁾ = h⁽ℓ⁻¹⁾ + Attn( RMSNorm(h⁽ℓ⁻¹⁾) )          (pre-norm attention)
h⁽ℓ⁾ = a⁽ℓ⁾  + SwiGLU( RMSNorm(a⁽ℓ⁾) )           (pre-norm MLP)
```

Pre-norm is chosen per `[S27]`, which shows post-norm requires warm-up because its initialisation-time
gradients are large and depth-independent. Full reasoning in [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.2.

### 4.2 RMSNorm

```
RMSNorm(x) = x / sqrt( (1/d)·Σ_j x_j² + ε )  ⊙  γ            ε = 1e-5
```

**Backward.** With `r = sqrt(m + ε)` and `m = (1/d)Σ x_j²`:

```
∂L/∂γ_j = (∂L/∂y_j) · (x_j / r)
∂L/∂x_j = (γ_j / r)·(∂L/∂y_j)  −  (x_j / (d·r³))·Σ_k γ_k (∂L/∂y_k) x_k
```

The second term is the **radial correction** — it projects the incoming gradient off the direction of `x`.
Dropping it is a common implementation bug that trains but does so incorrectly.

**Cost:** forward `d` MACs for the sum of squares; backward `≈ 3d`. Compare LayerNorm `[S21]`, which needs a
mean pass *and* a variance pass: `2d` forward and `≈ 4d` backward. **RMSNorm saves roughly half the
normalisation reduction work**, which is the concrete reason `[S22]` was adopted.

### 4.3 RoPE

Positions are encoded by rotating pairs of coordinates. For pair `i` at position `p` with base `Θ`:

```
ω_i = Θ^(-2i/d_h)                     i = 0 … d_h/2 − 1
q'_{2i}   = q_{2i} cos(ω_i p) − q_{2i+1} sin(ω_i p)
q'_{2i+1} = q_{2i} sin(ω_i p) + q_{2i+1} cos(ω_i p)
```

**The defining property.** With `R(p)` the block-diagonal rotation matrix:

```
⟨R(p)q, R(k)k⟩ = qᵀ R(p)ᵀ R(k) k = qᵀ R(k−p) k
```

The score depends only on the **relative offset** `k − p`. No parameters are added, and the score decays with
distance rather than saturating.

**Frequency spread.** For `d_h = 32`, `Θ = 10000`, the wavelengths run from `λ = 2π·Θ⁰ = 6.28` (fastest
pair) to `λ = 2π·Θ^{30/32} ≈ 3.53 × 10⁴` (slowest). The slowest wavelength exceeds `T_max = 2048` by a factor
of about **17**, so the highest-order dimensions rotate by only a small angle across the whole context — they
distinguish *coarse* position, while the fastest dimensions (`λ ≈ 6.28`) alias many times over.

**[OPEN]** `Θ = 10000` is conventional and untuned. Whether `T_max = 2048` is well matched to it is
unverified; the general practice of raising `Θ` for longer contexts suggests it may be larger than necessary.

### 4.4 Attention with a sliding causal window

For query position `t`, the attended set is `𝓐(t) = { s : max(0, t−W+1) ≤ s ≤ t }`.

```
P(t,s) = softmax_s( q_tᵀ k_s / √d_h )        s ∈ 𝓐(t),  −∞ elsewhere
o_t    = Σ_{s∈𝓐(t)} P(t,s) v_s
```

**Two distinct costs, never to be conflated:**

| Quantity | Value |
| --- | --- |
| Attended **pairs** | `N(T,W) = Σ_{t=0}^{T−1} min(t+1, W)` |
| Attended **positions** (the KV read) | `T · W` |

For `T = 2048, W = 256`: pairs = `N = 491,648`, positions = `524,288` — the window only begins to bite near
the end of the sequence, so they differ by just 6 %. They differ because early positions
have fewer than `W` predecessors. **The MAC count uses pairs; the memory bandwidth uses positions.**

### 4.5 Total forward MACs

Per layer, per token:

```
M_layer = 3d²            W_qkv
        + d²             W_o
        + 2·d·p          attention (scores + weighted sum), p = pairs at this position
        + 3·d·d_ff       SwiGLU
```

Plus the output head `V·d` **once per token** (not per layer). This is what
`tools/phase2_calc.py:prefill_macs()` computes, and it is the definition every other document references.

---

## 5. The backward pass, derived

**This section did not previously exist anywhere in the project.** The `6ND` convention in
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) was used as a citation to `[S9]`/`[S43b]` without
derivation. It can be derived exactly.

### 5.1 The linear-layer rule

For `y = Wx` with `W` of shape `d_out × d_in`, forward costs `d_out · d_in` MACs. Given `∂L/∂y`:

```
∂L/∂W = (∂L/∂y) xᵀ            →  d_out · d_in MACs
∂L/∂x = Wᵀ (∂L/∂y)            →  d_out · d_in MACs
```

**Therefore backward through a linear layer costs exactly `2×` its forward, and produces two gradients.**

This is the whole of the `6ND` result, and it is worth seeing directly because the constant `6` is otherwise
memorised rather than understood.

### 5.2 Applying it

| Component | Forward MACs/token | Backward MACs/token |
| --- | --- | --- |
| `W_qkv` | `3d²` = 196,608 | `6d²` = 393,216 |
| `W_o` | `d²` = 65,536 | `2d²` = 131,072 |
| `W_gate_up` + `W_down` | `3·d·d_ff` = 528,384 | `6·d·d_ff` = 1,056,768 |
| Attention scores + AV | `2·d·p` | `≈ 4·d·p` |
| RMSNorm | `d` | `≈ 3d` |
| RoPE, softmax, SiLU, residual | `O(d)` | `O(d)` |

**Every matmul term is exactly 2×.** The elementwise terms are 2–3× and are negligible by comparison.

### 5.3 The result

```
Forward  = 2·N·D  FLOPs          (2 FLOP per MAC, N params, D tokens)
Backward = 4·N·D  FLOPs          (exactly 2× forward)
─────────────────────────────
Total    = 6·N·D  FLOPs          ✓
```

**`6ND` is now derived, not asserted.** With activation checkpointing there is one extra forward pass:

```
Total_checkpointed = 2ND + 2ND + 4ND = 8·N·D
```

which is the `8ND` used in [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md).

### 5.3A The exact reconciliation

The derivation above is the *convention*; it is not the exact count. The two differ in a way that is small at
AETHER's training length and large at long context, and `tools/phase2_calc.py:flops_vs_6nd()` asserts the exact
identity for all three configs:

```
exact = 2ND  +  attention matmuls  −  2 × (norm parameters) × T
```

| Config | Exact forward FLOPs | `2ND` | Ratio |
| --- | --- | --- | --- |
| T | 62,685,184 | 58,540,032 | 1.071 |
| N | 992,083,968 | 942,211,072 | 1.053 |
| M | 9,429,843,968 | 8,627,945,472 | **1.093** |

The two corrections push in opposite directions:

- **Attention matmuls are omitted by `6ND`**, because they are data-dependent rather than parameter-borne.
  This makes `6ND` an underestimate, and the error grows as `O(T)`.
- **Norm parameters are over-counted by `6ND`**, because it charges each as though it were a matmul weight.
  Each RMSNorm parameter actually costs **2 FLOPs** per token, and there are `2d` per layer plus a final `d`.

At `T = 512` the first wins and `6ND` is 9.3 % low. At `T = 8192` the attention term dominates and `6ND`
understates by **3.0×**. §7A.2 of [`SCALING_LAW_ANALYSIS.md`](SCALING_LAW_ANALYSIS.md) gives the full table.

### 5.4 Where `6ND` is wrong

It is a **lower bound** and it omits, in decreasing importance:

| Omitted term | Rough magnitude at `d = 256` |
| --- | --- |
| Optimiser update (Adam: ~5 ops/param/step) | **Non-trivial over long runs** |
| Data loading, tokenisation, host↔device | Machine-dependent |
| Non-matmul elementwise in fwd/bwd | ~5–10 % |
| Gradient reduction (single-threaded: none) | 0 |
| Attention-specific overhead (masking, softmax) | Small at `W = 256` |

**[PROPOSED]** Treat any wall-clock estimate derived from `6ND` as a **lower bound**, and expect the real
figure to be 10–40 % higher. [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) already states the direction;
this section gives the reason.

---

## 6. Activation memory, derived

Training memory is dominated by stored activations. Per layer, per token, in `binary32` (4 bytes):

| Stored tensor | Values | Bytes |
| --- | --- | --- |
| RMSNorm output (2 sites) | `2d` | `8d` |
| `W_qkv` output | `3d` | `12d` |
| Attention probabilities (windowed) | `W` | `4W` |
| Attention output | `d` | `4d` |
| `W_gate_up` output | `2·d_ff` | `8·d_ff` |
| SiLU(gate) | `d_ff` | `4·d_ff` |
| SwiGLU product | `d_ff` | `4·d_ff` |
| Residual checkpoints | `2d` | `8d` |
| **Total per layer per token** | | **`≈ 32d + 16·d_ff + 4W`** |

At Config M (`d = 256, d_ff = 688, W = 256`): `32·256 + 16·688 + 4·256 = 8,192 + 11,008 + 1,024 = 20,224` bytes
per layer per token.

For `L = 8`, `T = 512`, `b = 8`: `20,224 × 8 × 512 × 8 = 662,700,032` bytes = **632.0 MiB** — **catastrophically over budget** for a 512 MiB target.

### 6.1 Checkpointing: the derivation

Store only *layer boundaries* and recompute each layer's internals during backward.

| Strategy | Activation memory | Extra FLOPs |
| --- | --- | --- |
| None | `b·T·(32d + 16·d_ff + 4W)·L·4` | 0 |
| Full (`√L` segments) | `b·T·d·√L·4` + one segment's internals | +1 forward |
| Every layer | `b·T·d·L·4` | +1 forward |

At Config M full checkpointing: `8 × 512 × 256 × 8 × 4 = 33,554,432` B = **32.00 MiB** of stored layer
boundaries, plus one layer's internals `20,224 × 512 × 8 = 82,837,504` B = **79.00 MiB**. **Total ≈ 111.0 MiB**
versus 632.0 — a **5.7× reduction** for a 33 % compute increase.

This is why [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6 makes checkpointing **mandatory** at Config M rather
than optional: without it the model does not train inside any plausible envelope. Note that the numbers here
(`T = 512`, `b = 8`) are a *worked example*, not the budgets in `MEMORY_BUDGET.md` §6 — those use a different
and more detailed accounting that includes optimiser state and fragmentation headroom.

**[OPEN]** The `√L` segmented scheme is strictly better than every-layer on memory and equally good on compute.
It is not specified in Phase 2 because it is an implementation complexity, and the first implementation should
prefer the simpler scheme.

---

## 7. Attention as matrix multiplication

A fact that matters for the 32-bit target, and is easily missed.

```
S = Q Kᵀ / √d_h          (T × T, or T × W windowed)
P = softmax(S)
O = P V
```

Shapes at `T = 2048`, `H = 8`, `d_h = 32`, `b = 8`:

| Tensor | Full attention | Windowed |
| --- | --- | --- |
| `S` | `b·H·T·T` = **268,435,456** values | `b·H·T·W` = 33,554,432 |
| `S` in `binary32` | **1.0 GiB** | **128.0 MiB** |

**A single full-attention score tensor at `T = 2048` is 1 GiB** — half of the 2 GiB envelope, for one
temporary. This is the strongest single argument for the window, and it is a *memory* argument, not a compute
one. [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.2 states it; this derives it.

### 7.1 The overflow, recomputed

The byte count `b·H·T·T·4 = 17,179,869,184` **exceeds `2³²` and wraps to exactly 0** in 32-bit arithmetic:

```
17,179,869,184 = 4 × 4,294,967,296 = 4 × 2³²  ⇒  ≡ 0 (mod 2³²)
```

An unchecked `size_t` multiply yields a successful **zero-byte allocation**. This is the derivation behind
[`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §5.1 and `E_OVERFLOW` in
[`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §8.

**[PROPOSED]** All size arithmetic is performed in `uint64_t` and narrowed only after a check against both
`SIZE_MAX` and a declared per-buffer ceiling.

---

## 8. Receptive field, derived

Layer 1 attends `W` tokens. Each further layer attends `W` tokens *of the previous layer's outputs*, and those
outputs themselves incorporate `W−1` additional positions. Hence:

```
RF(1) = W
RF(ℓ) = RF(ℓ−1) + (W − 1)
RF(L) = L·(W − 1) + 1
```

Inverting for the minimum window that spans `T_max`:

```
W_min = ⌈(T_max − 1)/L⌉ + 1
```

| Config | `L` | `W` | `RF` | `T_max` | Coverage | `W_min` |
| --- | --- | --- | --- | --- | --- | --- |
| M | 8 | 256 | 2,041 | 2,048 | 99.7 % | 257 |
| N | 4 | 128 | 509 | 512 | 99.4 % | 129 |
| T | 2 | 128 | 255 | 256 | 99.6 % | 129 |

**This derivation caught a real defect**: Config T was originally `W = 64, L = 2` → `RF = 127` against
`T_max = 256`, a 49.6 % shortfall. See [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5.3A.

---

## 9. Softmax: stability, gradient, and error

### 9.1 Max-subtraction

```
softmax(z)_i = exp(z_i − z_max) / Σ_j exp(z_j − z_max)
```

Mathematically a no-op (it cancels), numerically essential: without it, `exp(z)` overflows `binary32` at
`z > 88.7`. With it, every exponent is `≤ 0`, so the result is in `(0,1]` and the denominator is in
`[1, V]`. **Overflow becomes structurally impossible**, not merely unlikely
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9.6).

### 9.2 Gradient

With `p = softmax(z)` and upstream gradient `g`:

```
∂L/∂z_i = p_i ( g_i − Σ_j p_j g_j )
```

The parenthesised term is the **probability-weighted mean of the incoming gradient**. Consequences:

- The Jacobian is not diagonal, so every logit's gradient depends on every probability.
- When the softmax is saturated (`p_max ≈ 1`), the gradient vanishes for the dominant class and is
  proportional to the small probabilities for the rest — **this is the mechanism of softmax saturation
  failure**, and it is why logits must not be allowed to grow without bound.

### 9.3 Error sensitivity

```
dP_i / P_i ≈ dlogit_i − Σ_j P_j dlogit_j  ≈  dlogit_i        (for small perturbations)
```

A logit error of `ε` shifts each probability by about `ε` **relatively**. A token-selection change requires
the top-1/top-2 logit margin to be below `≈ 2ε`.

At `ε = 4.89 × 10⁻⁴` (`gamma_8192`, the head's `binary32` bound): margin `< 9.8 × 10⁻⁴` can flip.
At `ε ≈ 2.1 × 10⁻²` (int8 weights): margin `< 4.2 × 10⁻²` can flip — **a 43× larger vulnerable margin**, which
is why int8 needs its own tolerance ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9A.4).

---

## 10. Cross-entropy and bits-per-byte

### 10.1 The loss

```
L = −(1/N) Σ_{i=1}^{N} log p_θ(x_i | x_<i)
```

**Gradient with softmax:** remarkably clean. With `z` the logits and `t` the target index:

```
∂L/∂z_j = p_j − δ_{jt}
```

This is why the softmax and cross-entropy kernels are fused in every serious implementation: computing them
separately materialises the full `V`-sized probability vector and then differentiates through it, doing twice
the work for the same result.

### 10.2 Bits per byte — and why AETHER uses it

Per-token loss depends on the tokenizer, so two models with different vocabularies cannot be compared by
per-token loss. Bits-per-byte normalises by the *raw bytes* of the underlying text:

```
BPC = ( Σ_i −log₂ p_θ(x_i | x_<i) ) / ( bytes in the original text )
```

The conversion from a token-level average:

```
BPC = ( nll_nats_per_token / ln 2 ) × ( tokens / bytes )
```

The factor `tokens/bytes` is the tokenizer's inverse compression. **This is exactly what makes vocabularies
comparable**, and it is why [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) mandates BPC rather than perplexity.

| Vocabulary | Tokens/byte (typical) | Effect on BPC |
| --- | --- | --- |
| `V = 8192` | ~0.30 | Higher BPC for equal quality |
| `V = 32768` | ~0.25 | Lower BPC |
| `V = 50257` (GPT-2) | ~0.24 | Lower still |

**A smaller vocabulary is penalised by this metric** — a real and documented cost of AETHER's choice. It is the
correct metric anyway, because it measures the thing that matters (compression of actual text), and hiding
the penalty by reporting per-token perplexity would be dishonest.

### 10.3 Relation to perplexity

```
perplexity = 2^(BPC × bytes/token) = exp(nll_nats_per_token)
```

Perplexity is `V`-dependent and therefore **not** comparable across tokenizers. AETHER reports BPC.

---

## 11. Initialisation: variance propagation

### 11.1 Why `1/√d`

For `y = Wx` with `x ∈ ℝ^d` having i.i.d. entries of variance `v` and `W` with i.i.d. entries of variance `s²`:

```
Var(y_j) = Σ_i Var(W_ji) Var(x_i) = d · s² · v
```

To keep `Var(y) = v` (variance-preserving), require `d·s² = 1`, i.e. **`s = 1/√d`**. This is the
Xavier/He argument specialised to the case where the input is already normalised.

### 11.2 Why RMSNorm makes this simpler than usual

Because RMSNorm re-normalises to unit RMS before every sub-block, the *absolute* scale of activations does not
accumulate across layers — only the scale entering each sub-block matters, and that is fixed. This is why the
simple `1/√d` rule suffices and no depth-dependent correction is needed at `L = 8`.

Without normalisation, variance would compound and a `1/√(2L)` residual scaling would be required
([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.1 leaves this `[OPEN]`).

### 11.3 Why the down projection needs `1/√(3·d_ff)`

`W_down` consumes the SwiGLU product, which sums contributions from `d_ff` positions each combining **three**
terms (gate, up, and their product). Its variance is therefore `≈ 3·d_ff` times that of a single unit-variance
input. Using `1/√d` would inflate output variance by `√3 ≈ 1.73` per layer, compounding to `1.73^8 ≈ 57×`
across `L = 8`.

**This is the most likely place for an unnoticed initialisation bug**, because it trains — just badly.

### 11.4 Verified consistency

With `s = 1/√d` and unit-RMS activations, for `d_h = 32`:

```
Var(q_j) = d · s² = 1                    ⇒  q_j ~ N(0,1)
Var(q·k) = d_h · 1 = 32                  ⇒  std = 5.66
after 1/√d_h scaling: std = 5.66/√32 = 1.0
```

**Attention logits have standard deviation 1.0 at initialisation** — comfortably `O(1)`, with ~89× headroom
before `exp` overflow. Confirmed by `tools/phase2_calc.py:init_logit_std()`.

---

## 12. AdamW, written out

```
m_t = β₁ m_{t−1} + (1−β₁) g_t                        (first moment)
v_t = β₂ v_{t−1} + (1−β₂) g_t²                       (second moment)
m̂   = m_t / (1 − β₁ᵗ)                                (bias correction)
v̂   = v_t / (1 − β₂ᵗ)
θ_t = θ_{t−1} − η ( m̂ / (√v̂ + ε) + λ θ_{t−1} )       (AdamW: decay OUTSIDE the moment)
```

**The critical distinction** `[S28]`: in Adam-with-L2 the decay appears inside `g_t` and therefore passes
through `√v̂`, so parameters with large gradient history are decayed *less*. AdamW applies `λθ` directly. The
two are not equivalent, and the coupled form is a bug, not a variant.

**Why `β₂ = 0.95` and not `0.999`:** with `β₂ = 0.999` the second moment has an effective memory of ~1000
steps, which at short training runs never fully adapts. `0.95` gives ~20 steps. **[PROPOSED]** at AETHER's
scale — untested, and a candidate for the first ablation.

### 12.1 Memory

Three tensors of `N` in addition to parameters (`m`, `v`, and the parameters themselves), plus one gradient:
**`16 bytes/parameter`** at `binary32` — `4N` params + `4N` grads + `4N` m + `4N` v. This is the derivation
behind [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6.

---

## 13. What is derived versus assumed

| Result | Status |
| --- | --- |
| `P_layer = 4d² + 3·d·d_ff + 2d` | **Derived** — §2 |
| Backward = 2× forward ⇒ `6ND` | **Derived** — §5 |
| Activation memory `32d + 16d_ff + 4W` | **Derived** — §6 |
| `RF(L,W) = L(W−1)+1` | **Derived** — §8 |
| `b·H·T·T·4 ≡ 0 (mod 2³²)` | **Derived** — §7.1 |
| Logit std 1.0 at init | **Derived** — §11.4 |
| `β₂ = 0.95` appropriate | **[PROPOSED]** — untested |
| `Θ = 10000` appropriate for `T_max=2048` | **[OPEN]** |
| `ε = 1e-5` appropriate | **[OPEN]** — conventional |
| `d_ff` parity rule necessary | **[ASSUMPTION]** — reasonable, untested |

---

## 14. Unresolved questions

1. Does the `√L` segmented checkpointing scheme beat every-layer at Config M in practice? **[OPEN]**
2. Is `β₂ = 0.95` right, or should it be `0.999` at AETHER's short run lengths? **First ablation candidate.** **[OPEN]**
3. Should `Θ` be raised given `T_max = 2048`? **[OPEN]**
4. Is grouping the loss computation into 64-token blocks worth it at `V = 8192`, where the ungrouped buffer is only 2 MiB? **[OPEN]**
5. Does the `6ND` omission factor hold at 10–40 % for a scalar x87 kernel, or is it larger? **[OPEN]**
6. Should SiLU use the exact `σ(x)` or a polynomial approximation on the x87 path? **[OPEN]**

---

## 15. Status summary

| Item | Status |
| --- | --- |
| Parameter formula, all three configs | **Derived and verified** |
| SwiGLU parameter-to-compute ratio = 1:1 | **Derived** — §3.1 |
| Backward pass | **Derived — new in this document** |
| `6ND` and `8ND` | **Now derived**, previously asserted |
| Activation memory formula | **Derived** |
| Checkpointing 5.9× reduction | **Derived** |
| Full-attention 1 GiB score tensor | **Derived** |
| 32-bit wraparound to zero | **Derived** |
| BPC vs perplexity | **Derived** |
| Initialisation variance propagation | **Derived** |
| Anything measured | **None.** |
