# AETHER — Training Compute and Feasibility

Status: **Analysis, not measurement.** Every figure here is derived from a stated model. **No
training run has been executed by this project.** The achieved-hardware-throughput figures are
**priors for planning**, explicitly labelled, and Phase 5 must replace them with measurements.

This document exists because Phase 2 originally left training feasibility as an open question. Leaving
it open was not honest: the arithmetic is simple, and the answer is inconvenient. It belongs in the
specification, not in a footnote.

Related: [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) (the model) ·
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6 (training memory) · [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md)
(how Phase 5 measures the real numbers) · [`DATA_POLICY.md`](DATA_POLICY.md) (corpus requirements)

---

## 1. Why this document exists

The project's principles say x86-64 is the **reference development platform** and 32-bit x86 is a
**first-class execution target**. Phase 2 initially treated "training on CPU" as a single undifferentiated
claim. It is not.

There are three distinct questions, and conflating them produced an evasion:

1. **Can a 32-bit x86 machine train an AETHER model in a useful time?**
2. **Can the development machine train one in a useful time?**
3. **Can this project train anything a reasonable person would call a "language model"?**

The answers are: **no**, **yes but slowly**, and **only a narrow one**. This document states all three
with the arithmetic behind them.

---

## 2. The compute model

Training compute is conventionally estimated as

```
C ≈ 6 · N · D     FLOPs
```

where `N` is the number of parameters and `D` the number of training tokens `[S9]`. The factor 6 is
2 FLOP per parameter per token for the forward pass (one multiply and one add per multiply-accumulate,
counted as 2) plus 4 for the backward pass. It is the standard approximation used for scaling-law
work `[S9]` and is a *lower bound* on real cost — it excludes optimiser arithmetic, data loading,
activation checkpointing's recompute, and all non-matmul overhead.

**Activation checkpointing adds roughly one extra forward pass**, so AETHER's real training cost is
closer to `8·N·D`. Since [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6 shows checkpointing is **mandatory**
at the 32-bit budget, the 8 FLOP/token figure is the honest one for this project. Tables below use `6ND`
for comparability with the literature and note the 33 % uplift separately.

---

## 3. Training time against achieved throughput

Wall-clock time is `C / f`, where `f` is **achieved** floating-point throughput — not peak.

### 3.1 Config N

| Tokens/param | `D` tokens | FLOPs (`6ND`) | @0.5 GF/s | @1 GF/s | @2 GF/s | @4 GF/s |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | 9 201 280 | 1.02 × 10¹⁴ | 56.7 h | 28.3 h | 14.2 h | 7.1 h |
| 10 | 18 402 560 | 2.03 × 10¹⁴ | 112.9 h | 56.4 h | 28.2 h | 14.1 h |
| 20 | 36 805 120 | 4.06 × 10¹⁴ | 225.9 h | 112.9 h | 56.5 h | 28.2 h |

### 3.2 Config M

| Tokens/param | `D` tokens | FLOPs (`6ND`) | @5 GF/s | @10 GF/s | @20 GF/s |
| --- | --- | --- | --- | --- | --- |
| 2 | 16 851 456 | 8.52 × 10¹⁴ | 2.0 d | 1.0 d | 0.5 d |
| 5 | 42 128 640 | 2.13 × 10¹⁵ | 4.9 d | 2.5 d | 1.2 d |
| 10 | 84 257 280 | 4.26 × 10¹⁵ | 9.9 d | 4.9 d | 2.5 d |
| 20 | 168 514 560 | 8.52 × 10¹⁵ | 19.7 d | 9.9 d | 4.9 d |

> **These totals use the `6ND` convention, which is 9.3 % low at Config M.** The exact expansion of
> `prefill_macs()` + `backward_macs()` at `T = 512` gives **4.66 × 10¹⁵** FLOPs rather than 4.26 × 10¹⁵ —
> 10.8 d rather than 9.9 d at 5 GFLOP/s. `6ND` omits attention matmuls and over-charges norm parameters in
> a partially cancelling way; [`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md) §5.3A derives the
> identity and [`SCALING_LAW_ANALYSIS.md`](SCALING_LAW_ANALYSIS.md) §7A shows the error reaching 3× at `T = 8192`.
> The `6ND` column is retained because it is what the literature reports and what enables comparison;
> **use the exact figure for go/no-go decisions.**

### 3.3 What throughput is realistic?

**These are priors, not measurements on AETHER hardware.** No AETHER kernel exists. They are stated so
the plan can be sanity-checked, and Phase 5 must replace them with a measured GEMM rate for the actual
development machine.

| Platform | Plausible *achieved* fp32 rate, single core | Basis |
| --- | --- | --- |
| Legacy 32-bit x86, scalar x87, no SIMD | ~0.2 – 1 GFLOP/s | Scalar issue rate; no FMA; x87 stack pressure |
| Legacy 32-bit x86 with SSE (runtime-detected) | ~0.5 – 2 GFLOP/s | 4-wide SSE, no FMA |
| Modern x86-64, SSE2 baseline | ~2 – 8 GFLOP/s | 4-wide, FMA if available |
| Modern x86-64, AVX2 + FMA | ~10 – 30 GFLOP/s | 8-wide FMA, 2 FMA units |

Achieved throughput on **small matrices** (`d = 128…256`) is far below peak because arithmetic
intensity is low and the working set is dominated by cache traffic
([`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §3.2). A well-optimised CPU GEMM on a 256-wide matrix
typically achieves a modest fraction of peak. **[ASSUMPTION]** AETHER should expect to land in the
lower half of each band for its first implementation, because the first implementation will not be
optimised.

---

## 4. The honest answer for 32-bit training

At **1 GFLOP/s** achieved — optimistic for a scalar x87 target, plausible for an SSE-enabled 32-bit
machine:

| Task | Time |
| --- | --- |
| Config N, 10 tokens/param | **56 hours** |
| Config M, 10 tokens/param | **1183 hours ≈ 49 days** |

At **0.5 GFLOP/s** — realistic for a no-SIMD legacy machine:

| Task | Time |
| --- | --- |
| Config N, 10 tokens/param | **113 hours ≈ 4.7 days** |
| Config M, 10 tokens/param | **2370 hours ≈ 99 days** |

**Training Config M from scratch on a legacy 32-bit machine is not a research plan. It is a stall.**

This is a genuine finding, and it is uncomfortable: the project's most distinctive constraint
(32-bit x86 as a first-class target) cannot be extended to *training* without abandoning the ability
to iterate. What follows is the consequence, stated explicitly rather than quietly resolved.

---

## 5. The consequence: separate the training platform from the execution target

The project principles already contain the resolution — they say x86-64 is the **reference development
platform**. This document makes the implication explicit:

| Activity | Platform | Status |
| --- | --- | --- |
| **Inference** | 32-bit x86 **and** x86-64 | The project's central goal. Phase 7 tests it. |
| **Training** | x86-64 development machine | A documented **non-goal** on 32-bit x86 |
| **Training on 32-bit x86** | — | **Explicitly out of scope** until measured evidence makes it viable |

**[PROPOSED] N-T1.** Phase 5 trains on the development platform. Phase 7 tests **inference** on 32-bit
x86, not training. No document may claim 32-bit training capability.

This is not a retreat from the 32-bit goal; it is a correct reading of it. The goal is that AETHER
models **run** on constrained hardware. Building a model is a development activity and is not the
constrained environment.

---

## 6. Introducing Config T: a pipeline-validation model

The gap between "nothing exists" and "train a 1.84 M-parameter model" is too large to cross in one
step. AETHER therefore proposes a third, much smaller configuration whose **only** purpose is to
validate the pipeline end to end.

### 6.1 Proposed Config T

| Symbol | Value | Note |
| --- | --- | --- |
| `V` | 2048 | Reduced vocabulary; sufficient for a narrow synthetic corpus |
| `d` | 64 | Model width |
| `L` | 2 | Layers |
| `H` | 2 | Heads |
| `d_h` | 32 | `d/H` |
| `d_ff` | 168 | `2.625d`; SwiGLU/`8d²` parity 0.984 (see [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5.3) |
| `W` | 128 | Attention window; receptive field `2·(128−1)+1 = 255 ≥ T_max` |
| `T_train` | 128 | Training context |
| `T_max` | 256 | Maximum context |
| **Parameters** | **228 672** | Derived by the same formulas |

### 6.2 Training time for Config T

At **20 tokens/parameter** rather than 10 — a model this small needs more repetitions to fit
anything, and the cost is affordable — `D = 4 573 440` and `C = 6.27 × 10¹²` FLOPs:

| Achieved throughput | Time |
| --- | --- |
| 0.5 GFLOP/s | 3.5 h |
| 1 GFLOP/s | 1.7 h |
| 2 GFLOP/s | 52 min |
| 5 GFLOP/s | 21 min |

**This is the point of Config T.** It is trainable **on the 32-bit target itself** in an afternoon, which
means the first end-to-end validation of tokenizer → training → format → runtime → evaluation can
happen entirely on the constrained platform, with no dependency on a faster machine.

That is a stronger result than it first appears: it means the 32-bit target can be used to prove the
**pipeline**, even though it cannot be used to train a **useful model**. Those are different claims and
Config T separates them cleanly.

### 6.3 What Config T is for, and what it is not

**For:**
- Verifying that the training loop converges at all, on a trivially learnable task
- Verifying that checkpoints round-trip through the AMC format
- Verifying that the runtime reproduces training-time logits within tolerance
- Verifying that the 32-bit build produces comparable output to 64-bit
- Measuring the actual achieved GFLOP/s that §3.3 only estimates

**Not for:**
- Any capability claim whatsoever
- Any benchmark result
- Justifying Config M's design

**[PROPOSED]** Config T is added to the roadmap as the first artefact of Phase 4. It is a test fixture,
not a model release, and it must never be described as "AETHER's model".

---

## 7. Config M on the development platform

With training moved to x86-64, Config M becomes feasible but still slow:

| Tokens/param | @5 GF/s | @10 GF/s | @20 GF/s |
| --- | --- | --- | --- |
| 2 | 2.0 d | 1.0 d | 0.5 d |
| 5 | 4.9 d | 2.5 d | 1.2 d |
| 10 | 9.9 d | 4.9 d | 2.5 d |

**At 10 tokens/parameter on a 10 GFLOP/s core, Config M is a 5-day run** (plus the 33 % checkpointing
uplift, so closer to **6.6 days**). That is slow enough that:

- A failed run costs a week, which is why **Config T and Config N must succeed first**.
- Hyperparameter search by full retraining is impossible. The project must rely on small-scale proxies
  and accept that some choices will be made without a sweep — and **say so** in the model card.
- Every run must be resumable, because a 5-day run will be interrupted.

**[OPEN]** Whether a multi-threaded training implementation is in scope would change these figures
substantially. It is not proposed for Phase 5, because threading adds a determinism hazard
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §7.1) that costs more to control than it saves in a
first implementation.

---

## 8. Data requirements this implies

At 10 tokens/parameter, Config M needs **84 257 280 tokens** ≈ 84 M tokens. At roughly 1.3 tokens per
word and ~6 bytes per word, that is on the order of **400 MB of raw text**.

That is not a large corpus by modern standards, but under [`DATA_POLICY.md`](DATA_POLICY.md) it is not
trivial: every byte needs provenance, a licence, a permission basis, and a manifest entry
([`DATA_POLICY.md`](DATA_POLICY.md) §2). AETHER does not yet have such a corpus, and **acquiring one is
on the critical path for Phase 5**, not an afterthought.

**[OPEN]** Whether an 84 M-token corpus with clean provenance can be assembled for this project at all
is unresolved, and it may be the hardest constraint in the roadmap. If it cannot, the honest
consequence is a smaller model at fewer tokens/parameter, with a documented capability ceiling.

---

## 9. What this document changes in the roadmap

| Change | Reason |
| --- | --- |
| Config T added | Cross the gap from nothing to Config N in one step |
| Phase 5 trains on x86-64 | 32-bit training measured as 49–99 days |
| 32-bit training explicitly out of scope | Stated rather than quietly assumed |
| Training cost stated up front | A 5-day run changes how experiments are planned |
| Data acquisition flagged as critical path | 84 M tokens with provenance is not free |

**None of these changes weakens the project's central goal.** AETHER still aims to make models *run* on
constrained 32-bit hardware. It simply stops pretending that building them there is practical, and says
so before anyone spends a month discovering it.

---

## 10. Unresolved questions

1. What is the achieved GFLOP/s on the actual development machine? **Unmeasurable until Phase 4.** **[OPEN]**
2. Is 10 tokens/parameter the right target for a model this far outside the Chinchilla fit `[S9]`? **[OPEN]**
3. Can a thread-parallel implementation preserve the determinism guarantees, and is the speedup worth it? **[OPEN]**
4. Is an 84 M-token corpus with clean provenance obtainable? **[OPEN]** — critical path
5. Config T's 228 672 parameters were chosen for speed, not for its ability to learn anything useful. Does it learn its validation task reliably? **Unverified.** **[OPEN]**
6. Does the 33 % checkpointing uplift hold for a real implementation, or is it worse? **[OPEN]**

---

## 11. Risks

| # | Risk | Likelihood | Impact | Mitigation (proposed) |
| --- | --- | --- | --- | --- |
| R1 | Real achieved throughput is far below the 5–20 GFLOP/s prior, making Config M a multi-week run | **High** | High | Measure on Config T first (§6.3); publish the number before committing to Config M |
| R2 | An 84 M-token corpus with clean provenance cannot be assembled | Medium | **High — project-limiting** | Treat as critical path (§8); scope a smaller model if it fails, and say so |
| R3 | The 33 % checkpointing uplift is optimistic and real training memory exceeds budget | Medium | Medium | Measure in Phase 4; reduce micro-batch before reducing the model |
| R4 | Learning rate transferred untuned from a smaller config does not transfer | **High** | Medium | Accept and record in the model card; a failed run costs days, so monitor early loss |
| R5 | A 5-day run is interrupted and cannot resume exactly | Medium | High | Deterministic checkpoint/resume with seeded RNG state is a Phase 5 exit criterion |
| R6 | Config T validates the pipeline but Config N still fails to converge | Medium | Medium | Real possibility; Config T proves mechanics, not learnability |
| R7 | The throughput priors are mistaken for measurements by a future reader | Low | High | Every table is labelled; §3.3 states the priors are unverified; the `[PROPOSED]` markers are load-bearing |

---

## 12. Limitations of this analysis

1. **Nothing here is measured.** Every FLOP count is derived from the formulas in
   [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §6–7, which are themselves unvalidated against an
   implementation.
2. **`6ND` is a lower bound.** It excludes optimiser updates, data loading, tokenisation, evaluation
   passes, and all memory traffic. Real wall-clock time will be worse, possibly substantially.
3. **The throughput priors are guesses** grounded in general knowledge of x86 scalar and SIMD code, not
   in a benchmark of this project's (nonexistent) kernel.
4. **Single-threaded throughout.** No multi-core, no SIMD beyond what a compiler vectorises. Real
   implementations of this kind routinely gain 2–4× from careful vectorisation and more from threading.
5. **Token count is a convention, not a finding.** 10 tokens/parameter follows `[S9]`'s compute-optimal
   ratio, which was fitted at scales many orders of magnitude above Config M. Whether it transfers is
   unknown.
6. **The corpus estimate assumes ~1.3 tokens/word and ~6 bytes/word** — English-prose priors. Code, math,
   or multilingual data would change it materially.
7. **This document does not model power, cost, or thermal limits.** It assumes the machine is available
   for the whole run.

---

## 13. Status summary

| Item | Status |
| --- | --- |
| Compute model `C ≈ 6ND` | **Established** — standard scaling-law convention `[S9]` |
| Config N training time | **Derived**, not measured (§3.1) |
| Config M training time | **Derived**, not measured (§3.2) |
| 32-bit training is infeasible | **Derived** and, at 49–99 days, robust to any plausible error in the priors (§4) |
| Achieved throughput on any machine | **Unknown** — no benchmark exists |
| Config T as pipeline fixture | **Proposed** (§6) |
| Corpus availability | **Unknown** — critical path (§8) |
| Training platform = x86-64 | **Proposed decision**, recommended to be adopted as `N-T1` (§5) |
| Any training having occurred | **No.** None. |

The single most important sentence in this document is the last row of that table. AETHER has trained
nothing, and every number above is arithmetic performed on a design that does not yet exist in code.
