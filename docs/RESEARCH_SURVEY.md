# AETHER — Research Survey

Status: **Research document.** Every claim below is either attributed to a cited source or marked as
an AETHER assumption. **No experiment has been run by this project.** Nothing in this document is a
measured result of AETHER.

Scope: literature review supporting the Phase 2 design decisions for a CPU-first, 32-bit-x86-aware
model ecosystem. This document motivates; [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) decides.

---

## 0. How to read this document

Every statement carries a status marker:

| Marker | Meaning |
| --- | --- |
| **[ESTABLISHED]** | Reported and evaluated in the cited peer-reviewed or archival source. AETHER did not verify it independently. |
| **[PROPOSED]** | An AETHER design proposal. Not implemented, not tested. |
| **[ASSUMPTION]** | An explicit premise AETHER is proceeding on, which could be wrong. |
| **[UNVERIFIED]** | Something plausible that this survey could not confirm from a primary source. Not relied upon. |
| **[OPEN]** | An unresolved question, recorded rather than guessed at. |

Citation identifiers `[S#]` are stable across all Phase 2 documents. The full reference list is at the
end of this document ([§8](#8-references)).

**A caution about this survey.** Published results are produced on specific hardware, data, and
harnesses. None of them were produced on AETHER's target hardware, and none of them are directly
transferable to it. Where a paper reports a speedup, that speedup is a property of the paper's
implementation on the paper's hardware. AETHER does not inherit those numbers, and none are quoted
below as predictions of AETHER performance.

---

## 1. The central architectural question

AETHER must choose a sequence-mixing mechanism that is simultaneously:

1. cheap in **parameters** (small models are parameter-constrained, not compute-constrained);
2. cheap in **incremental decode cost** per generated token;
3. cheap in **memory** for both weights and per-token state;
4. **implementable in portable C** without vector-island assumptions;
5. **numerically stable** in 32-bit floating point on legacy units.

Condition 5 is the least discussed in the mainstream literature and is a first-class constraint here:
the ecosystem that produced most modern architectures assumes IEEE-754 `binary32` executed on
contemporary SSE/AVX units with a consistent evaluation model. On 32-bit x86 the situation is more
complicated — see [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2.

---

## 2. Sequence-mixing architectures

### 2.1 The Transformer

The Transformer replaced recurrence with scaled dot-product self-attention over the whole sequence
`[S1]`. For `T` tokens and model width `d`, one attention block costs:

| Component | MACs (prefill, length `T`) | MACs (decode, one token) |
| --- | --- | --- |
| QKV projection | `3 · T · d²` | `3 · d²` |
| Attention scores | `T² · d` | `T · d` |
| Value mixing | `T² · d` | `T · d` |
| Output projection | `T · d²` | `d²` |
| **Total** | **`4Td² + 2T²d`** | **`4d² + 2Td`** |

Three properties matter for AETHER:

- **Prefill is quadratic in `T`** through the `2T²d` term. At `T = 512`, `d = 256`, that term is
  33 % of attention cost; at `T = 4096` it is 89 %.
- **Decode is linear in context**, `2Td` per layer per token. This is the term sliding-window
  attention attacks.
- **The attention-score matrix is `H × T × T` in memory.** At `H = 8`, `T = 4096`, `binary32`, a
  single layer's score matrix is 512 MiB. This is the dominant memory risk at long context, and it is
  the single strongest argument against long-context full attention on a 32-bit budget
  ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4).

**[ESTABLISHED]** The Transformer's cost structure and its parallelisability are as described in
`[S1]`. **[PROPOSED]** AETHER does not adopt full global attention as a default; see §2.5.

### 2.2 Recurrent networks: LSTM and GRU

LSTM `[S2]` and GRU `[S3]` achieve constant state (`O(d)` per layer per direction) and constant
compute per token, which is ideal for the constrained target. Their costs:

- **No parallel computation over sequence positions.** Training is inherently sequential along the
  time axis unless chunked, truncated, or parallelised over the associativity of the recurrence —
  which gated units with nonlinearities do not generally permit exactly.
- **Long-range propagation** is limited by optimisation difficulty, which is exactly the problem LSTM
  was designed to mitigate `[S2]`.
- **Fetch-bound decode.** At batch 1 the layer is a sequence of small matrix-vector products, so
  arithmetic intensity is low and performance is dominated by memory traffic, not FLOPs.

**[ESTABLISHED]** The gating mechanisms and their motivation are as cited.
**[ASSUMPTION]** On a legacy CPU without wide SIMD, the recurrent approach's low arithmetic
intensity may be matched to the hardware better than an attention block's batched matmuls. This is
untested and is a candidate ablation ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §6).

### 2.3 Structured state-space models

S4 `[S4]` parameterised `A` as normal-plus-low-rank, enabling convolution-form training and linear-time
inference with a fixed state. Mamba `[S5]` made the state-space parameters input-selective, and
Mamba-2 `[S6]` formalised the duality between selective SSMs and masked attention through structured
semiseparable matrices.

For AETHER the relevant facts are:

- **State size is fixed and independent of `T`**, so memory does not grow with context. This is
  directly favourable.
- **Training in convolution form is efficient**, but the selective variant's scan is sequential. A
  parallel scan exists and is associative, but on a scalar CPU the benefit is bounded by available
  instruction-level parallelism.
- **Implementation complexity is high.** A correct selective scan with hardware-friendly state
  passing is substantially more intricate than a dense matmul block, and every component must be
  validated against a reference.

**[ESTABLISHED]** The mechanisms and their asymptotic properties are as cited.
**[PROPOSED]** AETHER does not adopt a selective SSM as its primary mechanism in Phase 2. The reason
is implementation risk per unit of expected benefit at AETHER's model scale, not a claim that SSMs are
worse. At `d = 256`, a dense matmul block is easier to get right, easier to verify numerically, and
easier to port to a scalar target. This may be revisited ([`ROADMAP.md`](ROADMAP.md) §Phase 8).

### 2.4 Gated linear recurrences and hybrids

RWKV `[S8]` formulates a linear-attention recurrence that is trainable in parallel and runs in
constant time per token at inference. Griffin `[S7]` combines an RG-LRU recurrent block with local
(sliding-window) attention in an alternating pattern.

**[ESTABLISHED]** Both are reported to approach Transformer quality at their evaluated scales while
retaining recurrent inference cost `[S7][S8]`.

The structural idea AETHER takes from `[S7]` is **the hybrid**: most layers do cheap local work,
and a minority do something with a wider receptive field. Alternating local-attention and
linear-recurrence blocks bounds both per-token compute and per-layer memory.

**[PROPOSED]** AETHER adopts a **narrowed** version of this idea for its primary architecture: local
(sliding-window) attention only, with the window as the sole long-range mechanism, deferring any
recurrent or global layer to a later variant. This is a deliberate reduction in ambition. See §2.5
for the argument and [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5 for the rejected alternatives.

### 2.5 Comparison against AETHER's criteria

Ratings are **AETHER's engineering judgement** based on the cited properties, not measured results.
"Legacy-CPU fit" is an **[ASSUMPTION]** column and is the least defensible one in this table.

| Criterion | Full attention `[S1]` | LSTM/GRU `[S2][S3]` | Selective SSM `[S5][S6]` | Gated linear recurrence `[S8]` | Sliding-window attention |
| --- | --- | --- | --- | --- | --- |
| Params at fixed `d` | Baseline | ~2.0–2.4× attention block | ~1.3–1.6× | ~1.5–2.0× | Baseline (same as attention) |
| Prefill compute | `O(T²d)` | `O(T·d²)`, sequential | `O(T·d²)`, scan | `O(T·d²)`, chunked | `O(T·W·d)` |
| Decode compute/token | `O(T·d)` | `O(d²)` constant | `O(d²)` constant | `O(d²)` constant | `O(W·d)` constant |
| Decode state memory | `O(H·T·d)` KV cache | `O(d)` | `O(d·state)` | `O(d)` | `O(H·T·d)` KV, attention over `W` |
| Peak transient memory | `O(H·T²)` scores | `O(d)` | `O(d·state)` | `O(d)` | `O(H·W·T)` |
| Training parallelism | Full over `T` | Sequential over `T` | Scan (parallelisable) | Chunked | Full over `T` |
| Implementation complexity | **Low** | Low | **High** | High | **Low** |
| Numerical-stability risk | Moderate (softmax, large logits) | Moderate (vanishing/exploding) | **High** (state decay, scan precision) | Moderate | Moderate (same as attention) |
| Verifiability against a reference | Easy | Easy | **Hard** | Hard | Easy |
| Legacy-CPU fit (assumption) | Poor at long `T` | Good | Uncertain | Uncertain | Good |
| Maturity of reference implementations | High | High | Moderate | Moderate | High |

Reading of this table:

- **Low implementation complexity and easy verification are worth more than asymptotic elegance at
  AETHER's current stage**, because AETHER has no reference implementation, no test corpus, and one
  maintainer.
- **Sliding-window attention keeps the attention block AETHER can verify easily** while removing the
  two terms that break the memory budget: `O(T²)` scores and `O(T)` decode cost.
- **The cost of that choice is real**: no mechanism with unbounded receptive field. A sliding window
  is a genuine capability limit, not a free optimisation. It is stated as a limitation, not sold as
  an advantage.

**[OPEN]** Whether a hybrid (some recurrent layers, some local-attention layers) materially beats
pure local attention at 1–10 M parameters on AETHER's target is unknown. It is a Phase 8 ablation, not
a Phase 2 assumption.

---

## 3. CPU and memory constraints

### 3.1 The 32-bit address space

The figure that governs AETHER's memory design is the user-mode virtual address space on a 32-bit
process, not the nominal 4 GiB.

| Platform | Typical user-mode VA | Note |
| --- | --- | --- |
| Linux i386 | 3 GiB | Default `PAGE_OFFSET` split |
| Windows 32-bit | 2 GiB | Default; `/3GB` and `LARGEADDRESSAWARE` may raise it on some configurations |
| Either, with PAE or 4G/4G variants | configuration-dependent | Not assumed by AETHER |

**[ASSUMPTION]** AETHER budgets against **2 GiB of user address space** as the conservative case, and
plans for a **512 MiB working envelope** for the runtime. Rationale in
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2. Using the smaller number is deliberate: designing to the
best case is how portability claims become untestable.

Three consequences that are not obvious:

1. **`size_t` is 32 bits.** Any `size_t` arithmetic on sizes derived from a file can wrap. All
   size/offset computation must use checked arithmetic with explicit width, and must be validated
   *before* any allocation ([`SECURITY_MODEL.md`](SECURITY_MODEL.md) §4).
2. **Virtual ≠ resident.** `mmap`ing a file maps address space without resident pages, but a
   sequential pass over it faults pages in. Fragmentation of a multi-hundred-MiB VA over a long
   uptime is a real failure mode; a single large contiguous allocation may fail even when the total
   free VA is sufficient.
3. **Physical RAM is usually smaller than VA.** A machine with 512 MiB of RAM has the same 4 GiB VA
   ceiling. Working-set, not address space, is often the binding constraint.

### 3.2 Cache and memory bandwidth

For batch-1 decode the operation is a stream of matrix-vector products. Each weight is read once and
used once, giving arithmetic intensity near `2 FLOP/byte` for `binary32`. **[ASSUMPTION]** Such a
workload is memory-bandwidth-bound, not FLOP-bound, which means:

- **Weight layout matters more than instruction selection.** Row-major weights, read sequentially, at
  cache-line granularity, are the target.
- **Quantisation is primarily a bandwidth optimisation**, not a compute optimisation, on targets
  without integer-dot-product instructions. Halving bytes halves the traffic; AVX2/npmmadd does not
  exist on such targets, and emulating it costs more instructions than the bytes saved.
- **L2/L3 sizing determines blocking strategy.** A 256 KiB L2 is common on legacy parts; a
  per-layer weight block larger than L2 will thrashe. This argues for layer-major execution and
  modest `d`.

These are **[ASSUMPTION]**s from first principles, not measurements. Phase 9 is where they get tested.

### 3.3 Instruction sets and SIMD portability

| Feature | i386 baseline | x86-64 | AETHER stance |
| --- | --- | --- | --- |
| x87 FPU | Guaranteed | Present but deprecated | Correct-but-slow fallback only |
| SSE | Requires CPUID check | Guaranteed | Optional path |
| SSE2 | Requires CPUID check (introduced Pentium 4 era) | **Guaranteed by the ABI** | Baseline vector path on x86-64; runtime-detected on i386 |
| SSE3–SSE4 | Requires CPUID check | Optional | Not assumed |
| AVX/AVX2 | Requires CPUID + OS support (XSAVE) | Not guaranteed | Not assumed |
| `FMA` | Not guaranteed | Not guaranteed | Not assumed |
| Integer dot-product / VNNI | Absent | Not guaranteed | Not assumed |

The asymmetry matters: **code that is "portable" because it compiles for x86-64 has not been shown to
run correctly on i386.** SSE2 is guaranteed on x86-64 and optional on i386. AETHER therefore requires
runtime CPU dispatch with a scalar path that is correct on every target, and treats every vector path
as an optional acceleration validated against the scalar one
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §6).

**[PROPOSED]** Phase 4–6 code targets the scalar path first, correct by construction. Vector paths are
added only behind a dispatch layer and only when a bit-comparable or tolerance-checked equivalence
test exists.

### 3.4 Floating-point: the x87 evaluation-model problem

On i386, floating-point may be evaluated on the x87 unit, which computes in 80-bit extended precision
and stores to 64-bit or 32-bit. The C standard exposes this as `FLT_EVAL_METHOD`. The consequences:

- **Double rounding** is possible: a `binary32` expression computed in extended precision and then
  narrowed can differ from the same expression rounded once to `binary32`.
- **Results can differ between builds** depending on `-mfpmath`, register spills, and optimisation
  level, even on one machine.
- **x86-64 uses SSE by default**, where `FLT_EVAL_METHOD == 0`, so the discrepancy is invisible on the
  development platform and appears only on the 32-bit target.

This is a reproducibility problem as much as a correctness one, and it directly affects the
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) requirement that 32-bit and 64-bit outputs be comparable.
AETHER's stance is in [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2.3.

### 3.5 Integer arithmetic

32-bit integer multiply is single-instruction on all targets; 64-bit multiply (`int64`) on i386 is
emulated and costly. `int32` accumulation overflows quickly in a matmul of dimension `d > 32` with
large operands, so narrower accumulation requires an explicitly justified bound on operand magnitude
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §4.3).

---

## 4. Numerics and quantisation

### 4.1 Formats

| Format | Bits | Exponent | Mantissa | Max finite | Notes for AETHER |
| --- | --- | --- | --- | --- | --- |
| `binary32` (fp32) | 32 | 8 | 23 | ~3.40 × 10³⁸ | Native on x87/SSE; the safe default |
| `binary16` (fp16) | 16 | 5 | 10 | 65504 | **No native i386 arithmetic**; must be emulated; overflow-prone |
| `bfloat16` | 16 | 8 | 7 | ~3.39 × 10³⁸ | Same exponent range as fp32; no native i386 arithmetic |
| `int8` | 8 | — | — | — | Storage and (on some targets) dot-product |
| `int4` | 4 | — | — | — | Storage only on AETHER's targets |

**[ESTABLISHED]** Format parameters are from IEEE 754 `[S26]` and the definition of bfloat16 as an
8-bit-exponent/7-bit-mantissa truncation of fp32 with the same range and lower precision.

The decisive point for AETHER: **fp16 and bf16 are storage formats on i386, not compute formats.**
Converting to them and back costs instructions and gains nothing computational on a target with no
native support. Where the literature reports speedups from low-precision arithmetic, those speedups
are properties of GPU tensor cores or of CPUs with native support. AETHER does not inherit them.

**[PROPOSED]** `binary32` is the compute and accumulation format for all AETHER numerics through
Phase 8. Narrower formats are considered for **weight storage only**, with dequantisation on read.

### 4.2 Quantisation methods

- **LLM.int8()** `[S15]` isolates outlier features into a higher-precision path, addressing the
  observation that a small number of activation channels dominate the range. On i386 the mixed-precision
  path is costly, so this technique's benefit is uncertain without native int8 dot products.
- **GPTQ** `[S16]` is a one-shot second-order weight quantisation to 3–4 bits with reported
  degradation described as negligible at large scale.
- **SmoothQuant** `[S17]` migrates activation-quantisation difficulty into weights via an equivalent
  scaling, enabling W8A8.
- **AWQ** `[S18]` protects a small fraction of salient weight channels using activation statistics,
  hardware-efficiently.
- **BitNet b1.58** `[S19]` is a *from-scratch* ternary-weight training scheme, not a post-training
  quantiser. It is relevant to AETHER because AETHER also trains from scratch.

**[ESTABLISHED]** The reported behaviour of these methods is as cited, at the scales and on the
hardware of their respective papers. **[ASSUMPTION]** None of it transfers to a 1–10 M parameter model
on a scalar CPU without measurement. In particular, quantisation error at 3–4 bits on an 8 M parameter
model may be far larger than at 70 B parameters, where the same relative error is absorbed by
redundancy that small models do not have. **[OPEN]** whether int8 weight-only storage is
quality-neutral for AETHER's models is unknown and is a Phase 8 experiment.

### 4.3 Accumulation precision

**[ESTABLISHED]** Quantised inference conventionally accumulates in a wider integer type than the
operands. The conventional choice for int8 operands is `int32`.

**[PROPOSED]** AETHER accumulates int8 products in `int32` and state a bound: with 8-bit operands
(≤ 127 magnitude) and a reduction length `K`, the worst-case magnitude is `K · 127² ≈ 16129K`, which
exceeds `int32` only for `K > 133 000`. For any AETHER block dimension this is safe. This is the
*safe* approach; narrower accumulation (`int16`) would require a per-block magnitude bound and an
overflow check, and is not proposed.

---

## 5. Tokenisation

### 5.1 Approaches

| Approach | Vocab | OOV risk | Determinism | Implementation cost |
| --- | --- | --- | --- | --- |
| Byte-level (raw UTF-8 bytes) | 256 | None | Exact | Trivial |
| Character-level | Language-dependent | Low | Exact | Low |
| BPE `[S11]` | Tunable | None if byte-initialised `[S14]` | Exact | Moderate |
| Unigram / SentencePiece `[S12][S13]` | Tunable | None if byte-fallback | Exact with fixed Viterbi | Higher |

Key points from the sources:

- **BPE** `[S11]` represents open-vocabulary text as subword units learned by iterative merging, which
  was introduced to remove the fixed-vocabulary limitation of word-level models.
- **Byte-level BPE** `[S14]` initialises the vocabulary with all 256 byte values, so every input is
  representable and no unknown token is ever required. This is the property AETHER most wants.
- **Unigram** `[S12]` models segmentation probabilistically and can yield several segmentations,
  which is a benefit for regularisation and a complication for exact reproducibility if sampling is
  used at encode time. SentencePiece `[S13]` implements both BPE and unigram without pre-tokenisation,
  treating input as a raw character stream.

### 5.2 Vocabulary size and memory

Embedding parameters are `V · d` and are usually the largest single tensor in a small model. For
AETHER's proposed Config M (`d = 256`, 8.43 M parameters), `V = 8192` gives a 2 097 152-parameter
embedding — **25.0 % of the model**. Doubling `V` to 16384 would add another 2.1 M parameters (+25 %)
for a text-compression gain of a few percent on short contexts. That trade is bad at AETHER's scale.

**[PROPOSED]** `V = 8192` for the first implementation, with the exact value treated as a Phase 3
decision informed by measurement on the target corpus. Rationale in
[`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §2.

### 5.3 UTF-8 and determinism

UTF-8 has the property that a byte sequence can be validated as it is decoded, and that invalid
sequences are detectable `[S14]` (a byte-level tokenizer permits arbitrary bytes but decoding must
still decide what to do with invalid ones). AETHER's requirement is:

- **Encode is a pure function of the input bytes.** Same bytes in, same token IDs out, on every
  platform, forever, for a fixed vocabulary version.
- **Decode may be lossy for invalid input** but must never be undefined: invalid sequences are
  replaced deterministically with U+FFFD, and this is documented rather than incidental.

Detail in [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md).

---

## 6. Training feasibility

### 6.1 What is established

- **Compute-optimal scaling** `[S9]`: for a fixed compute budget, parameters and training tokens
  should be scaled together, roughly 20 tokens per parameter in the Chinchilla regime. AETHER's models
  are far outside the regime in which these fits were made, so the constant is a starting point, not a
  law.
- **Small models can produce coherent text on constrained, narrow data.** TinyStories `[S10]` reports
  that models below 10 M total parameters, and even single-block architectures, produce fluent and
  consistent short stories when the training corpus is restricted in vocabulary and structure. That
  paper's contribution is as much about *data organisation* as about model size.
- **Parallel training of linear recurrences** `[S8][S5]` is achievable via chunking or scan.

### 6.2 What is not established

- **That a constrained machine can train a useful general-purpose language model.** No source
  supports this, and this project does not claim it. `[S9]` quantifies the compute required for
  general-purpose capability; the figures are far beyond a legacy CPU. The scope of AETHER's training
  claims is therefore narrow and must remain narrow until measured
  ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8).
- **That CPU training at AETHER's scale is practical in wall-clock terms.** It may be possible and
  still be too slow to be useful. The difference matters, and Phase 5 must report both.

### 6.3 Training memory

Training memory is dominated not by parameters but by **activations retained for the backward pass**,
plus optimizer state. With AdamW `[S20]`, a fully-trained `binary32` model needs `4` bytes/parameter
for weights, `4` for gradients, and `8` for the two moment estimates — **16 bytes/parameter before any
activation is stored**.

For AETHER Config M (8 425 728 parameters) that is **128.57 MiB** of fixed cost. Activations for a
micro-batch of 8 at 512 tokens add roughly **1.45 GiB**, which does not fit a conservative 32-bit
budget. **Activation checkpointing is therefore not optional — it is a design requirement**, reducing
activation storage by roughly the layer count at the cost of a second forward pass. The arithmetic is
in [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6.

This is a concrete, quantified consequence of the 32-bit constraint, discovered during this phase, and
it changes the Phase 5 design rather than being discovered during it.

---

## 7. Summary of what the survey supports

| Question | Answer supported by evidence | Status |
| --- | --- | --- |
| Is full attention optimal for constrained memory? | No — `O(T²)` scores dominate | **[ESTABLISHED]** `[S1]` |
| Are recurrent/SSM alternatives viable in principle? | Yes, in their papers' settings | **[ESTABLISHED]** `[S2][S5][S7][S8]` |
| Are they the right first choice for AETHER? | **No — implementation and verification risk is too high at 8 M parameters with one maintainer** | **[PROPOSED]** |
| Does sliding-window attention bound memory and decode cost? | Yes, by construction | **[ESTABLISHED]** (arithmetic) |
| Does it cost capability? | Yes — bounded receptive field | **[ESTABLISHED]** |
| Is fp16/bf16 compute viable on i386? | No native support; storage only | **[ESTABLISHED]** `[S26]` |
| Is int8 weight storage quality-neutral at 8 M params? | **Unknown** | **[OPEN]** |
| Can a constrained CPU train a general-purpose LM? | **Not supported by any source** | **[ESTABLISHED]** as a negative |
| Can it train a narrow, task-specific model? | Plausible; `[S10]` suggests data narrowness is a lever | **[ASSUMPTION]** |
| Is 32-bit x86 compatibility demonstrated? | **No.** No build exists | **[OPEN]** |

### Unresolved questions carried forward

1. Receptive-field adequacy of a pure sliding window at AETHER's scale. **[OPEN]**
2. Whether hybrid recurrence improves the quality-per-flop trade at 1–10 M parameters. **[OPEN]**
3. Quantisation tolerance of an 8 M parameter model at int8 and below. **[OPEN]**
4. x87 double-rounding effect on output equivalence between 32- and 64-bit builds. **[OPEN]**
5. Whether CPU training wall-clock is acceptable at the Nano configuration. **[OPEN]**
6. Practical achievable tokens/second on the target hardware — **no estimate is offered here, because
   no measurement exists.**

---

## 8. References

Every source below was checked to exist at the stated identifier during the preparation of this
document. AETHER does not claim to have independently validated any reported result.

- **[S1]** Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł.,
  Polosukhin, I. "Attention Is All You Need." arXiv:1706.03762 (2017).
  <https://arxiv.org/abs/1706.03762>
- **[S2]** Hochreiter, S., Schmidhuber, J. "Long Short-Term Memory." *Neural Computation* 9(8):
  1735–1780 (1997). <https://doi.org/10.1162/neco.1997.9.8.1735>
- **[S3]** Cho, K., van Merriënboer, B., Gulcehre, C., Bahdanau, D., Bougares, F., Schwenk, H.,
  Bengio, Y. "Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine
  Translation." arXiv:1406.1078 (2014). <https://arxiv.org/abs/1406.1078>
- **[S4]** Gu, A., Goel, K., Ré, C. "Efficiently Modeling Long Sequences with Structured State
  Spaces." arXiv:2111.00396 (2021); ICLR 2022. <https://arxiv.org/abs/2111.00396>
- **[S5]** Gu, A., Dao, T. "Mamba: Linear-Time Sequence Modeling with Selective State Spaces."
  arXiv:2312.00752 (2023). <https://arxiv.org/abs/2312.00752>
- **[S6]** Dao, T., Gu, A. "Transformers are SSMs: Generalized Models and Efficient Algorithms
  Through Structured State Space Duality." arXiv:2405.21060 (2024); ICML 2024.
  <https://arxiv.org/abs/2405.21060>
- **[S7]** De, S., Smith, S. L., Fernando, A., Botev, A., Cristian-Muraru, G., Gu, A., Haroun, R.,
  Berrada, L., Chen, Y., Srinivasan, S., Desjardins, G., Doucet, A., Budden, D., Teh, Y. W.,
  Pascanu, R., De Freitas, N., Gulcehre, C. "Griffin: Mixing Gated Linear Recurrences with Local
  Attention for Efficient Language Models." arXiv:2402.19427 (2024).
  <https://arxiv.org/abs/2402.19427>
- **[S8]** Peng, B., et al. "RWKV: Reinventing RNNs for the Transformer Era." arXiv:2305.13048
  (2023). <https://arxiv.org/abs/2305.13048>
- **[S9]** Hoffmann, J., Borgeaud, S., Mensch, A., et al. "Training Compute-Optimal Large Language
  Models." arXiv:2203.15556 (2022). <https://arxiv.org/abs/2203.15556>
- **[S10]** Eldan, R., Li, Y. "TinyStories: How Small Can Language Models Be and Still Speak Coherent
  English?" arXiv:2305.07759 (2023). <https://arxiv.org/abs/2305.07759>
- **[S11]** Sennrich, R., Haddow, B., Birch, A. "Neural Machine Translation of Rare Words with Subword
  Units." arXiv:1508.07909 (2015); ACL 2016. <https://arxiv.org/abs/1508.07909>
- **[S12]** Kudo, T. "Subword Regularization: Improving Neural Network Translation Models with
  Multiple Subword Candidates." arXiv:1804.10959 (2018); ACL 2018.
  <https://arxiv.org/abs/1804.10959>
- **[S13]** Kudo, T., Richardson, J. "SentencePiece: A simple and language independent subword
  tokenizer and detokenizer for Neural Text Processing." arXiv:1808.06226 (2018); EMNLP 2018 Demo.
  <https://arxiv.org/abs/1808.06226>
- **[S14]** Radford, A., Wu, J., Child, R., Luan, D., Amodei, D., Sutskever, I. "Language Models are
  Unsupervised Multitask Learners." OpenAI technical report (2019). Byte-level BPE tokenisation with a
  50 257-token vocabulary. (Technical report; not peer-reviewed.)
- **[S15]** Dettmers, T., Lewis, M., Belkada, Y., Zettlemoyer, L. "LLM.int8(): 8-bit Matrix
  Multiplication for Transformers at Scale." arXiv:2208.07339 (2022).
  <https://arxiv.org/abs/2208.07339>
- **[S16]** Frantar, E., Ashkboos, S., Hoefler, T., Alistarh, D. "GPTQ: Accurate Post-Training
  Quantization for Generative Pre-trained Transformers." arXiv:2210.17323 (2022); ICLR 2023.
  <https://arxiv.org/abs/2210.17323>
- **[S17]** Xiao, G., Lin, J., Seznec, M., Wu, H., Demouth, J., Han, S. "SmoothQuant: Accurate and
  Efficient Post-Training Quantization for Large Language Models." arXiv:2211.10438 (2022);
  ICML 2023. <https://arxiv.org/abs/2211.10438>
- **[S18]** Lin, J., Tang, J., Tang, H., Yang, S., Chen, W.-M., Wang, W.-C., Xiao, G., Dang, X.,
  Gan, C., Han, S. "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration."
  arXiv:2306.00978 (2023); MLSys 2024. <https://arxiv.org/abs/2306.00978>
- **[S19]** "The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits." arXiv:2402.17764
  (2024). Ternary-weight (`{-1, 0, 1}`) from-scratch training scheme (BitNet b1.58).
  <https://arxiv.org/abs/2402.17764>
- **[S20]** Kingma, D. P., Ba, J. "Adam: A Method for Stochastic Optimization." arXiv:1412.6980
  (2014); ICLR 2015. <https://arxiv.org/abs/1412.6980>
- **[S21]** Ba, J. L., Kiros, J. R., Hinton, G. E. "Layer Normalization." arXiv:1607.06450 (2016).
  <https://arxiv.org/abs/1607.06450>
- **[S22]** Zhang, B., Sennrich, R. "Root Mean Square Layer Normalization." arXiv:1910.07467 (2019);
  NeurIPS 2019. <https://arxiv.org/abs/1910.07467>
- **[S23]** Hendrycks, D., Gimpel, K. "Gaussian Error Linear Units (GELUs)." arXiv:1606.08415
  (2016). <https://arxiv.org/abs/1606.08415>
- **[S24]** Su, J., Lu, Y., Pan, S., Murtadha, A., Wen, B., Liu, Y. "RoFormer: Enhanced Transformer
  with Rotary Position Embedding." arXiv:2104.09864 (2021). <https://arxiv.org/abs/2104.09864>
- **[S26]** IEEE. "IEEE Standard for Floating-Point Arithmetic." IEEE Std 754-2019.
  <https://doi.org/10.1109/IEEESTD.2019.8766229>
- **[S27]** Xiong, R., Yang, Y., He, D., Zheng, K., Zheng, S., Xing, C., Zhang, H., Lan, Y., Wang, L.,
  Liu, T.-Y. "On Layer Normalization in the Transformer Architecture." arXiv:2002.04745 (2020);
  ICML 2020. <https://arxiv.org/abs/2002.04745>
- **[S28]** Loshchilov, I., Hutter, F. "Decoupled Weight Decay Regularization." arXiv:1711.05101
  (2019); ICLR 2019. <https://arxiv.org/abs/1711.05101>

### Sources deliberately not cited

- **Blog posts, course notes, and vendor marketing.** Not used as evidence, though some informed the
  framing. Where a fact appears above it is traceable to a listed source.
- **Reported runtime/throughput numbers from any paper.** Not quoted. They are properties of the
  authors' implementations and hardware, and quoting them here would invite exactly the misleading
  comparison [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §7 forbids.
- **Secondary summaries of `[S19]`.** The paper is cited by title and identifier. Its author list was
  verified during the Phase 2 citation audit and now appears in
  [`RESEARCH_REFERENCES.md`](RESEARCH_REFERENCES.md) §3B. The paper remains a **preprint**.
