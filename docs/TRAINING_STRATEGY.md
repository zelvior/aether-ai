# AETHER — Training Strategy

Status: **Design proposal.** No training has been run. Every figure is derived, not measured. The
resource estimates rest on throughput priors that Phase 5 must replace with measurements.

Related: [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) (the compute arithmetic) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A (initialisation, optimiser) ·
[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) (precision) ·
[`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) (how runs are recorded) ·
[`DATA_POLICY.md`](DATA_POLICY.md) (corpus requirements)

---

## 1. The separation this document exists to make

**Training requirements and inference requirements are different requirements, and conflating them
produced a false constraint in earlier planning.**

| | Training | Inference |
| --- | --- | --- |
| Where it runs | x86-64 development machine | target hardware, incl. 32-bit x86 |
| Precision | `binary32` throughout | `binary32` compute, int8 storage optional |
| Memory | 128–310 MiB with checkpointing | 13–100 MiB peak |
| Duration | hours to days, once | milliseconds per token, always |
| Frequency | a handful of times in the project's life | every use, forever |
| Optimised for | throughput | latency and footprint |

A model may be **trained on a stronger machine and designed for efficient inference on a weaker one.**
That is not a compromise; it is how essentially all deployed models are produced. This document states
it explicitly so no later reader infers that a 32-bit machine must train AETHER.

The consequence is already recorded in [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §5: 32-bit
*training* is an explicit non-goal (`N-T1`).

---

## 2. Initialisation

Full specification in [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.1. Summary and rationale here:

| Tensor | Init | Why |
| --- | --- | --- |
| Embeddings, attention projections, gate/up | `N(0, 1/d)` | Preserves variance into RMSNorm |
| Down projection | `N(0, 1/(3·d_ff))` | Compensates `3·d_ff` fan-in |
| RMSNorm gains | `1.0` | Identity start |
| Biases | none | None exist |

**The down-projection scaling is not cosmetic.** Its input has `3·d_ff` contributions from a gated
product; leaving it at `1/d` roughly triples per-layer output variance, which compounds across `L = 8`
layers to about `√(3^8)/√8 ≈ 6.5×` in standard deviation. Measured arithmetic, not guesswork:
`NUMERICAL_STRATEGY.md` §9.6 confirms `N(0, 1/d)` gives unit-variance `q` and `O(1)` attention logits,
which is the consistency check available without a run.

**[OPEN]** Whether residual-output scaling `1/√(2L)` is additionally needed at `L = 8`. Probably not;
"probably" is the honest confidence level.

---

## 3. Objectives

### 3.1 The default: next-token prediction

Standard causal language modelling with cross-entropy:

```
L = −(1/N) Σ_i log p(x_i | x_<i)
```

Advantages at AETHER's scale: one loss, one pass, no auxiliary heads, no extra parameters, and every
token contributes a training signal — which matters when the token budget is the binding constraint.

### 3.2 The alternatives, and why they are deferred

| Objective | Evidence | AETHER's position |
| --- | --- | --- |
| Masked / span corruption | `[S45]` compares objectives at 11 B | **Deferred** — bidirectional attention complicates the incremental KV cache, which is central to AETHER's inference design |
| Multi-token prediction | `[S49]` reports sample-efficiency gains | **Deferred to Phase 8** — plausible win, needs the pipeline to exist first |
| Prefix-LM | `[S45]` includes it | **Deferred** — needs two attention masks in one model |
| Contrastive / representation | Not an LM objective | **Out of scope** — AETHER ships a generator |

**[PROPOSED]** Any change of objective must be justified by a D-series comparison
([`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §6.1) on a fixed corpus, not
by appeal to results at a different scale.

---

## 4. Optimisation

Full table in [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.3. Rationale:

| Choice | Reason | Source |
| --- | --- | --- |
| AdamW | Decoupled decay is correct for adaptive methods | `[S28]` |
| `β₂ = 0.95` | Lower than 0.999 default; conventional for LMs | `[S28]` context, not a result |
| No warm-up | Pre-norm gradients are well-behaved | `[S27]` |
| Cosine decay, no restarts | Monotone schedule is easier to resume | `[S41]` |
| Global-norm clipping 1.0 | Cheap insurance | Standard practice, no single citation |
| Decay excludes norms and embeddings | Decaying a normalisation gain attenuates the signal | Reasoning, `[S22]` |

### 4.1 Gradient accumulation

The micro-batch is limited by memory ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6.3), not by anything
statistical. Accumulation restores an effective batch size:

| Config | Micro-batch | Accumulation | Effective batch (tokens) |
| --- | --- | --- | --- |
| Config T | 8 | 4 | 4,096 |
| Config N | 4 | 8 | 8,192 |
| Config M | 2 | 16 | 16,384 |

**[PROPOSED]** These are memory-driven defaults. Accumulation is exact — gradients sum, so the result
is indistinguishable from a larger batch except for any batch-dependent layer, and AETHER has none
(no batch norm, no dropout).

### 4.2 What is deliberately absent

- **No mixed precision.** `RESEARCH_SURVEY.md` §4 and `NUMERICAL_STRATEGY.md` §3: fp16/bf16 have no
  native arithmetic on the i386 baseline, so introducing them into training would create a numerical
  environment that cannot be reproduced on the target.
- **No loss scaling.** Follows from no mixed precision.
- **No dropout** (`ARCHITECTURE_SPEC.md` §8A.5) — a nondeterminism source that would complicate
  equivalence testing, at a scale where over-fitting is not the first-order risk.

---

## 5. Data pipeline

### 5.1 The stages, in order

```
raw ──> dedup ──> filter ──> language ID ──> tokenise ──> shuffle ──> pack ──> train
        (§5.2)   (§5.3)      (§8)            (TOKENIZER)  (§5.4)    (§5.5)
```

Every stage is deterministic given its inputs and seed, and every stage writes a manifest. A run that
cannot be reproduced from its manifest is not a valid run
([`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §2).

### 5.2 Deduplication

`[S42]` finds near-duplicate text and long repeated substrings pervasive in web corpora, over 1 % of
unprompted output copied verbatim from training data, and train–test overlap affecting over 4 % of a
standard validation set. At AETHER's data scale the consequence is larger, not smaller: a passage
repeated 60,000 times is negligible in a trillion-token corpus and catastrophic in an 84 M-token one.

| Stage | Method | Threshold |
| --- | --- | --- |
| Exact line dedup | Hash set | — |
| Near-dup paragraph | MinHash / suffix automaton over long substrings | **[PROPOSED]** 50-token window |
| Train/test overlap | Exact substring match against eval sets | **Zero tolerance** |

The third row is not an optimisation. Train–test overlap inflates measured capability, and an inflated
number is worse than no number.

### 5.3 Filtering

Cheap, deterministic, and conservative — the cost of dropping good data at this scale is lower than
keeping bad data:

| Filter | Rule |
| --- | --- |
| Length | Drop documents under 32 tokens or over sequence budget after packing |
| Repetition | Drop documents whose most frequent token exceeds 50 % of tokens |
| Encoding validity | Drop anything that is not valid UTF-8 |
| Control characters | Drop documents dominated by non-printing code points |

**[OPEN]** Whether a learned quality classifier is affordable. It would be a second model, and
AETHER's identity constraint applies to it as well.

### 5.4 Shuffling and packing

Documents are shuffled with a seeded PRNG and packed into fixed-length sequences with a document
boundary token so attention does not cross documents.

| Concern | Handling |
| --- | --- |
| Resumability | Shuffle order derived from `(seed, epoch, index)`, never from a running RNG |
| Determinism | Same seed + same corpus ⇒ same batches, bit for bit |
| Padding waste | Packed sequences; a trailing partial sequence is dropped, not padded |

### 5.5 Contamination prevention

`[S42]`'s 4 % overlap finding is the empirical basis for AETHER's zero-tolerance rule. The evaluation
corpora (`EVALUATION_PLAN.md` §2) are held out **before** dedup and never enter the pipeline.

---

## 6. Checkpointing and resumability

A Config M run is expected to take days ([`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §7). A
run that cannot resume exactly is a run that will be lost.

### 6.1 What a checkpoint must contain

| Item | Size (Config M) | Why |
| --- | --- | --- |
| Weights | 32.14 MiB | — |
| Adam first moment | 32.14 MiB | Adam does not forget |
| Adam second moment | 32.14 MiB | — |
| Step counter, LR | bytes | Schedule position |
| RNG state | bytes | Reproducible shuffling and init |
| Data cursor | bytes | Exact resume position |
| Corpus manifest hash | bytes | Detect a changed corpus |

**Total ≈ 96.5 MiB per Config M checkpoint** (weights plus two moment tensors), plus a small header.
At 3 rotating checkpoints that is ~290 MiB of disk — acceptable on the development machine, and the
reason checkpoints are **not** required to fit in the 32-bit envelope.

### 6.2 Resume must be exact, and that is testable

**[PROPOSED]** The Phase 5 exit criterion is: train for `k` steps, checkpoint, kill, resume, train `k`
more — and obtain the **same loss curve** as an uninterrupted `2k`-step run, to within floating-point
reproducibility. If the curves diverge, something in the pipeline is order-dependent that should not
be.

---

## 7. Scheduling for a multi-day run

| Concern | Mitigation |
| --- | --- |
| Interruption | Rotating checkpoints every N steps; exact resume §6.2 |
| Silent divergence | Log loss every step; abort on non-finite loss |
| Slow failure | Validate on held-out data at fixed intervals; abort if validation worsens for 3 intervals |
| Wasted days | **Run Config T and N first.** A pipeline bug found at Config M costs days |

The last row is the most important and is the reason Config T exists.

---

## 8. Multilingual data balance

AETHER targets English, Urdu, Hindi and Roman Urdu ([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §5).

| Language | Script | Data availability | AETHER position |
| --- | --- | --- | --- |
| English | Latin | Abundant | Dominant share |
| Hindi | Devanagari | Moderate | Underserved; upsampled |
| Urdu | Perso-Arabic (RTL) | Scarce | Underserved; upsampled |
| Roman Urdu | Latin (non-standard) | Very scarce, no standard orthography | **Special handling** |

**[OPEN]** The balance ratios are a maintainer decision and depend on what corpus is actually
obtainable ([`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §8). They are **not** set in Phase 2
because setting them without a corpus would be a fabricated plan.

**Capability is not coverage.** A tokeniser that encodes Urdu without error does not imply the model
understands Urdu. `TOKENIZER_SPEC.md` §5.4 states this explicitly; it is repeated here because
multilingual claims are the easiest in this project to overstate.

---

## 9. Reproducibility requirements

| Requirement | Implementation |
| --- | --- |
| Seed control | One seed; all derived streams derived from it by a documented rule |
| Corpus versioning | Content hash recorded in every run |
| Config capture | Full hyperparameters serialised, not summarised |
| Environment capture | Compiler, version, flags, architecture |
| Determinism | No dropout, no nondeterministic threading, documented reduction order |
| Negative results | **Recorded in the same log as positive ones** |

The last row is a policy commitment, not a technical one, and it is the one most often abandoned.

---

## 10. Risks

| # | Risk | Impact | Mitigation |
| --- | --- | --- | --- |
| R1 | Corpus unavailable at required scale (§8) | **Project-limiting** | Scope down and document |
| R2 | A multi-day run loses progress | High | §6.2 exact-resume test as exit criterion |
| R3 | Loss diverges and is only noticed late | High | §7 abort-on-non-finite; validation guard |
| R4 | Pre-norm without warm-up destabilises at `L=8` | Medium | `[S27]` argues against; fallback is to add warm-up |
| R5 | Untuned LR transferred from Config T hurts Config M | Medium | Record in model card; monitor early loss |
| R6 | Multilingual share is set arbitrarily and hurts all languages | Medium | §8 — left open deliberately |
| R7 | Train/test contamination inflates results | **High (invalidates results)** | Zero-tolerance overlap check §5.2 |

---

## 11. Unresolved questions

1. Is an 84 M-token corpus with clean provenance obtainable? **Critical path.** **[OPEN]**
2. Effective batch 16,384 tokens — is that right at this scale? Untuned. **[OPEN]**
3. Should the objective stay pure next-token, or adopt multi-token prediction in Phase 8? **[OPEN]**
4. What multilingual ratios are justified by an actually obtainable corpus (§8)? **Maintainer decision.** **[OPEN]**
5. Is a learned quality filter affordable, and does it violate the from-scratch constraint? **[OPEN]**
6. Does pre-norm truly avoid warm-up at `d=256, L=8`? `[S27]` says probably; unmeasured. **[OPEN]**

---

## 12. Status summary

| Item | Status |
| --- | --- |
| Training platform = x86-64 | **Proposed decision** (`N-T1`) |
| Initialisation | **Proposed**, consistent with `NUMERICAL_STRATEGY` §9.6 |
| Optimiser (AdamW, cosine, no warm-up) | **Proposed**, sourced to `[S28]`, `[S41]`, `[S27]` |
| Objective (next-token) | **Proposed**; alternatives deferred with reasons |
| Data pipeline stages | **Specified**, not implemented |
| Deduplication thresholds | **Proposed**, not validated |
| Checkpoint + exact resume | **Specified**; exactness is a Phase 5 test |
| Multilingual ratios | **Deliberately unresolved** |
| Any actual training | **None.** |
