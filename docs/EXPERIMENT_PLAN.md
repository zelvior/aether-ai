# AETHER — Experimental Programme

Status: **Costed plan.** No experiment has been run. Every figure is derived from
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md)'s compute model with checkpointing
(`C ≈ 8·N·D`) and the throughput priors stated there. **None of the timings is a measurement.**

Related: [`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) (admissibility rules) ·
[`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5.1/§6 (what the experiments
test) · [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §2–3 (the arithmetic) ·
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) (how results are reported)

---

## 1. The question this document costs out

[`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5.1 identifies the project's
central uncertainty:

> Is AETHER in a **power-law regime**, where capability per parameter is flat and small models are
> simply worse? Or a **threshold regime**, where specific capabilities are absent below some size and
> then appear abruptly?

**These imply opposite strategies, and guessing wrong wastes years.**

| If power law | If threshold |
| --- | --- |
| Maximise `P`; accept narrow data | Accept a capability ceiling |
| Architecture choice matters little | Architecture choice matters enormously |
| Invest in training compute | Invest in tools, memory, retrieval |
| Config M is a stepping stone | Config M is the destination |

The point of this document is that **this is cheap to answer.** The complete programme below costs
about **5 days of compute at 10 GFLOP/s**.

---

## 2. The configuration ladder

Three sizes, deliberately spread across a 37× range:

| Config | Parameters | Step from previous |
| --- | --- | --- |
| T | 228,672 | — |
| N | 1,840,256 | **8.05×** |
| M | 8,425,728 | **4.58×** |

**[PROPOSED]** Unequal spacing is intentional: a log-spaced ladder with a large first step tests whether
*anything* emerges between "toy" and "plausible", and the smaller second step gives a finer read on the
slope.

### 2.1 All three configs are already specified

No new architecture work is needed — Config T
([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5.4), N (§5.2) and M (§5.1) exist, and all share the
same layer structure, normalisation, activation, position scheme and objective. **Only the dimensions
change**, which is exactly what a controlled comparison requires
([`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §4).

---

## 3. Experiment E1 — the regime test

**The single most informative experiment in the project.**

| Parameter | Value |
| --- | --- |
| Varied | `P` only (§2) |
| Held fixed | Corpus, tokens/parameter, objective, optimiser, tokenizer, seed |
| Tokens/parameter | **5** (low, to make E1 affordable — see §3.2) |
| Seeds | 1 per size, variance bounded separately by E2 |
| Metric | Bits-per-byte on held-out data ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §3) |

| Config | `D` (tokens) | FLOPs | @10 GFLOP/s | @20 GFLOP/s |
| --- | --- | --- | --- | --- |
| T | 1,143,360 | 2.09 × 10¹² | **0.0 d** (hours) | — |
| N | 9,201,280 | 1.35 × 10¹⁴ | **0.2 d** | 0.1 d |
| M | 42,128,640 | 2.84 × 10¹⁵ | **3.3 d** | 1.6 d |
| **Total** | | **2.98 × 10¹⁵** | **3.4 d** | **1.7 d** |

### 3.1 What counts as a result

Plot `BPC` against `log P`. Two shapes, two conclusions:

| Shape | Interpretation | Action |
| --- | --- | --- |
| Straight line on log-log | **Power-law regime** | Larger `P` is the path; plan for it |
| Flat below N, drop at M | **Threshold regime** | Find the threshold; invest around it |
| Flat everywhere | **Saturated at 5 tok/param** | Run E3 before concluding anything |

**The third row is the trap.** A flat curve at 5 tokens/parameter may mean the models are data-starved,
not that scale does not matter. E1 is therefore never interpreted alone.

### 3.2 Why 5 tokens/parameter and not 10

Affordability. At 10 tokens/parameter E1 costs roughly `(10/5)² = 4×` more — about 11 days at
10 GFLOP/s instead of 3.4. The ratio question E1 asks ("does more `P` help at fixed `D/P`?") is
answerable at 5.

**The risk is stated plainly:** a 5-token/parameter model may be too undertrained to reveal a
power law that exists. E3 (§5) is what distinguishes "no power law" from "too little data".

---

## 4. Experiment E2 — the noise floor

Without this, E1's result cannot be interpreted: a difference smaller than seed variance is not a
difference.

| Parameter | Value |
| --- | --- |
| Config | **N** (affordable, representative) |
| Varied | Seed only |
| Seeds | **5** |
| Everything else | Fixed |

| Item | Value |
| --- | --- |
| Per run | 1.35 × 10¹⁴ FLOPs |
| Per run @10 GFLOP/s | 3.8 h |
| **Total (5 seeds)** | **18.8 h ≈ 0.8 d** |

### 4.1 What E2 produces

| Output | Use |
| --- | --- |
| Mean and standard deviation of final BPC | The noise floor |
| Spread of the loss curve | Whether curves are comparable at all |
| Whether 5 seeds suffice | Possibly needs more — stated if so |

**A difference between Config N and Config M smaller than E2's standard deviation is not evidence of
anything** and must be reported as indistinguishable
([`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §5).

### 4.2 The honest limitation

E2 measures variance at **N**, and applies it to **M**. Seed variance generally *decreases* with scale,
so applying N's floor to M is **conservative** — it will treat real M-sized differences as noise rather
than the reverse. That is the right direction to be wrong in.

---

## 5. Experiment E3 — is AETHER data-starved?

| Parameter | Value |
| --- | --- |
| Config | **N** |
| Varied | `D` (tokens/parameter) |
| Values | 5, 10, 20 |
| Everything else | Fixed |

| Tokens/param | `D` | FLOPs | @10 GFLOP/s |
| --- | --- | --- | --- |
| 5 | 9,201,280 | 1.35 × 10¹⁴ | 3.8 h |
| 10 | 18,402,560 | 2.71 × 10¹⁴ | 7.5 h |
| 20 | 36,805,120 | 5.42 × 10¹⁴ | 15.1 h |
| **Total** | | **9.48 × 10¹⁴** | **26.4 h ≈ 1.1 d** |

**20 tokens/parameter is `[S9]`'s Chinchilla ratio** — the upper bound of reasonable practice. If BPC is
still falling steeply at 20, AETHER is data-limited and no architecture change will fix it.

---

## 6. The whole programme

| Experiment | Answers | FLOPs | @10 GFLOP/s | @20 GFLOP/s |
| --- | --- | --- | --- | --- |
| E1 regime test | Does scale help? | 2.98 × 10¹⁵ | 3.4 d | 1.7 d |
| E2 seed variance | How much is noise? | 6.77 × 10¹⁴ | 0.8 d | 0.4 d |
| E3 data scaling | Is data the limit? | 9.48 × 10¹⁴ | 1.1 d | 0.5 d |
| **E4 LR transfer** | Is the transfer assumption valid? | 2.71 × 10¹⁴ | **0.3 d** | 0.2 d |
| **Total** | | **4.87 × 10¹⁵** | **≈ 5.6 d** | **≈ 2.8 d** |

### 6.1 E4 — the learning-rate transfer test

Added by [`OPTIMISATION_THEORY.md`](OPTIMISATION_THEORY.md) §4.1, because the documentation had been assuming
that a learning rate tuned at `d = 64` transfers to `d = 256` without justification.

| Run | Learning rate | Config | FLOPs | @10 GFLOP/s |
| --- | --- | --- | --- | --- |
| N @ `η_T` | as tuned on T | N | 1.35 × 10¹⁴ | 3.8 h |
| N @ `η_T/√2` | scaled by the `√` correction | N | 1.35 × 10¹⁴ | 3.8 h |
| **Total** | | | **2.71 × 10¹⁴** | **7.5 h** |

If the scaled value wins, the transfer bias is real and μP `[S50]` should be adopted before Config M training.
If neither is distinguishable from the other, E2's noise floor says the question is unanswerable at this scale —
which is itself a finding, and must be reported as such rather than as a null result.

**Five days of compute, at a pessimistic 10 GFLOP/s, decides the project's central strategic question.**

For context, [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §7 estimates a *single* Config M run at
10 tokens/parameter as roughly 5–6.6 days. **The entire experiment programme costs less than one
Config M training run.** That is the single most actionable finding of Phase 2.

---

## 7. What must be true before E1 runs

The programme is cheap only if the machinery works. Prerequisites, in order:

| # | Prerequisite | Phase | Blocks |
| --- | --- | --- | --- |
| 1 | Tokenizer round-trips on all four languages | 3 | Everything |
| 2 | Forward pass verified against a hand-checked reference | 4 | Everything |
| 3 | Training loop trains Config T to a nonzero result | 4 | E1 |
| 4 | Checkpoint → AMC → reload → identical output | 4 | E1 |
| 5 | Corpus assembled with provenance | 5 | E1 |
| 6 | BPC evaluation harness | 5 | E1 |

**None of these exists.** E1 cannot start until they do, and the 5-day figure assumes they are correct —
a pipeline bug found during E1 costs re-runs.

---

## 8. What this programme will not answer

| Question | Why not |
| --- | --- |
| Does Config M have useful *capability*? | BPC is not capability; no benchmark at this scale is meaningful |
| Is the architecture optimal? | E1 varies `P`, not architecture — that is D1, and it is a separate programme |
| Does AETHER run on 32-bit? | Nothing to do with training; see [`PLATFORM_COMPATIBILITY_PLAN.md`](PLATFORM_COMPATIBILITY_PLAN.md) |
| Is multilingual capability achieved? | Requires per-language evaluation data that does not exist |

**A successful E1 establishes one thing only:** whether capability scales smoothly or in steps across
AETHER's size range. That is narrow and it is worth 5 days because everything else depends on it.

---

## 9. If E1 says "threshold"

The most consequential possible outcome, and the one AETHER should plan for.

If capabilities appear abruptly between N and M, then:

- **Config M is the minimum viable model**, and there is no point training anything smaller except as a
  pipeline fixture.
- The six-component ecosystem stops being an architectural preference and becomes **the only path to
  usefulness** — tools, retrieval and memory supply what the Core structurally cannot.
- [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §4's lever ranking inverts:
  data quality matters less than *reaching the threshold*.

**AETHER does not know which outcome to expect, and this document does not claim to.** It claims only
that the answer is five days away.

---

## 10. Unresolved questions

1. Is 5 tokens/parameter enough to reveal a power law if one exists (§3.2)? **[OPEN]**
2. Do 5 seeds at N adequately bound variance, or is more needed? **[OPEN]**
3. Is BPC the right dependent variable, or should E1 also report token-level accuracy? **Proposed:
   BPC only — it is the only metric with a clean definition at this scale.** **[OPEN]**
4. Should E1 include Config T at all, or is it too small to inform anything? **Proposed: include it as
   the low anchor and as the pipeline sanity check.** **[OPEN]**
5. What corpus? The programme needs a single fixed corpus across all runs, and none exists. **[OPEN]**
6. Do the timings assume the 33 % checkpointing uplift throughout? **Yes, `C ≈ 8·N·D`.** **[OPEN]**

---

## 11. Status summary

| Item | Status |
| --- | --- |
| Regime question identified | **§1**, from `INTELLIGENCE_DENSITY_RESEARCH` §5.1 |
| E1 regime test | **Costed** — 3.4 d @10 GFLOP/s |
| E2 seed variance | **Costed** — 0.8 d |
| E3 data scaling | **Costed** — 1.1 d |
| Total programme | **≈ 5.3 d @10 GFLOP/s**, less than one Config M run |
| Prerequisites | **6, none existing** |
| Any run executed | **None.** |
| Compute figures measured | **None** — derived from priors |
