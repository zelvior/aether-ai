# AETHER — Intelligence Density Research

Status: **Research framework, not measurement.** This document proposes how to *think about and
measure* capability per unit of resource. It reports **no measurement of AETHER**, because nothing has
been trained or built.

Related: [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) (architecture comparison) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) (the model) · [`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md)
(data and objectives) · [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) (how capability is measured at all)

---

## 1. The objective, stated precisely enough to be wrong

The project's stated objective is:

> Maximum useful intelligence per parameter, per byte of memory and per unit of computation.

This is three objectives in one sentence, and they **conflict**. A model can be parameter-efficient and
compute-hungry (deep recurrence), or memory-efficient and parameter-wasteful (heavy weight sharing), or
compute-efficient and memory-hungry (large KV cache traded for throughput). A document that optimises
"intelligence density" without saying *which denominator* is not saying anything.

### 1.1 Why a single scalar metric would be dishonest

A universal "intelligence per parameter" number has three fatal problems:

1. **No agreed intelligence measure.** MMLU `[S43]`, ARC `[S44]` and bits-per-byte
   ([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §3) are not commensurable. Averaging them produces a
   number with no unit.
2. **Denominators are not independent.** Parameters correlate with memory; memory with cache behaviour;
   compute with latency. Dividing by one silently rewards inflating another.
3. **Ratios are unstable near zero.** A model at chance accuracy on a hard benchmark has a
   density-of-zero; the ratio becomes noise amplified by the denominator.

**AETHER therefore does not propose an intelligence-density metric.** It proposes a **measurement
matrix** with explicit units, explicit conditions, and an explicit refusal to collapse.

---

## 2. The measurement matrix

Every capability claim AETHER makes must be reported as a row, not a score. A row is:

| Axis | Symbol | Unit | Measured how |
| --- | --- | --- | --- |
| Capability | `C` | task-native (accuracy, BPC, exact-match %) | [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §2 |
| Parameters | `P` | count (dimensionless integer) | `ARCHITECTURE_SPEC.md` §6 |
| Storage | `M_store` | bytes on disk | `MEMORY_BUDGET.md` §3 |
| Peak inference memory | `M_peak` | bytes RSS | `MEMORY_BUDGET.md` §5 |
| Training compute | `F_train` | FLOPs | `TRAINING_FEASIBILITY.md` §2 |
| Inference compute | `F_inf` | FLOPs/token | `ARCHITECTURE_SPEC.md` §7 |
| Wall-clock latency | `L` | seconds/token | `EVALUATION_PLAN.md` §7 |

### 2.1 The four density quotients

Each quotient answers a **different question** and none is "the" answer:

| Quotient | Formula | Question it answers | Where it misleads |
| --- | --- | --- | --- |
| **Data efficiency** | `C / F_train` | How much capability per FLOP spent learning? | Favours tiny models that saturate early |
| **Storage density** | `C / M_store` | How much capability per byte shipped? | Favours models that shift work to runtime |
| **Runtime density** | `C / (F_inf · L)` | How much capability per second of use? | Ignores memory entirely |
| **Parameter density** | `C / P` | How much capability per parameter? | Rewards over-training a small model |

**[PROPOSED]** AETHER reports all four, never one, and never an average of them.

### 2.2 Why these units and not "intelligence"

Each numerator is a **task-specific, defined, reproducible** measurement. None requires defining
intelligence. AETHER makes no claim to measure intelligence; it measures task performance under stated
conditions and reports the resource cost of obtaining it.

---

## 3. Parameter-sharing mechanisms and their real accounting

### 3.1 Weight tying

AETHER ties the token embedding and output projection (`ARCHITECTURE_SPEC.md` §6). The saving is exact
and countable:

| Config | Untied | Tied | Saved |
| --- | --- | --- | --- |
| Config M | 10,522,880 | 8,425,728 | **2,097,152 (19.9 %)** |
| Config N | 2,888,832 | 1,840,256 | **1,048,576 (36.3 %)** |

**[ESTABLISHED]** the arithmetic; **[PROPOSED]** that tying does not hurt quality at AETHER's scale.
`[S45]` reports tied embeddings as competitive in its ablations, but at 11 B parameters. At Config N,
tying removes 36 % of all parameters — a saving so large that the quality question is worth answering
empirically before accepting either answer.

### 3.2 Vocabulary as a parameter-efficiency decision

`P_emb = V · d` and the head is tied to it, so **vocabulary directly sets the parameter floor**. This
is the single largest lever AETHER has:

| `V` | Config N embedding params | Share of 1,840,256 |
| --- | --- | --- |
| 2048 | 262,144 | 14.2 % |
| 4096 | 524,288 | 28.5 % |
| 8192 | 1,048,576 | **57.0 %** |
| 16384 | 2,097,152 | 114 % (impossible at this `d`) |

**Config N is 57 % embedding.** That is a finding, not a footnote: at `d = 128`, a large vocabulary
consumes most of the budget on a lookup table. [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §3 trades
vocabulary size against sequence length because of exactly this table.

### 3.3 Recurrent parameter reuse

A recurrent architecture with `L` layers unrolled `n` times uses `P ∝ L` parameters but `n·L` steps of
compute. It therefore scores **well** on `C/P` and **badly** on `C/F_inf` and `C/(F_inf·L)`. This is
the clearest case where the four quotients disagree, and it is why §2.1 reports them separately.

**[OPEN]** No AETHER configuration uses recurrent weight reuse. The trade is noted because
`ARCHITECTURE_SPEC.md` §10 Alternative B is a hybrid that could.

### 3.4 Adapting vs. training: a distinction the literature blurs

`[S46]` covers **parameter-efficient adaptation** — adding a few trainable parameters to a large
pre-trained model. That is a different problem from **base-model parameter efficiency**, which is
AETHER's. A model that adapts efficiently can still be 1000× too large to ship.

AETHER's constraint is storage and runtime memory, so adaptation efficiency is a Phase 9+ concern at
most. It is cited here to prevent a plausible-sounding confusion.

---

## 4. What actually moves the needle at AETHER's scale

Ranked by expected effect at Config M, with the honest caveat that **none of these has been measured**:

| Lever | Expected effect | Confidence | Evidence |
| --- | --- | --- | --- |
| Data quality / narrowness | **Large** | Moderate | `[S10]` — capability emerges early under a narrow distribution |
| Deduplication | Moderate | Moderate | `[S42]` — fewer steps to target accuracy |
| Vocabulary size | Moderate (parameter accounting is exact) | High on accounting, low on quality | §3.2 |
| Weight tying | Moderate (accounting exact) | High on accounting | §3.1 |
| Tokens per parameter | Moderate | Low at this scale | `[S9]` fitted far above |
| Objective choice | Unknown | Very low | `[S45]` measured at scale |
| Architecture family | Unknown | Very low | `RESEARCH_SURVEY.md` §2 |
| Quantisation | Zero effect on `P`, large on `M_store` | High | `RESEARCH_SURVEY.md` §4 |

**The most important entry is the last one.** Quantisation is the only lever with a large, *certain*
effect on a resource axis (storage) and a bounded, measurable effect on capability. That is why
AETHER's roadmap puts it in Phase 8 rather than treating it as a stretch goal.

**The second most important is the first.** `[S10]`'s result suggests data distribution matters more
than architecture at this scale — which is uncomfortable for a project whose identity is architectural.
It is stated plainly because believing otherwise without evidence would be the more serious error.

---

## 5. The relationship between the axes

```
   P (parameters) ──determines──> M_store  (exactly, given dtype)
        │
        ├──determines──> F_inf  (≈ 2P FLOPs/token, plus attention term)
        │
        └──determines──> M_peak (weights + activations + KV)

   F_train ≈ 6 · P · D ──where D is chosen, not determined
```

The one genuinely free variable is `D`. Everything else follows from `P` and the architecture. This is
why [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) treats the tokens-per-parameter choice as the
central trade and why §4 lists it as "low confidence".

### 5.1 The diminishing-returns shape AETHER expects, and cannot yet verify

Scaling-law work `[S9]` fits a power law `C ∝ P^α` in the region where it was fitted. AETHER operates
several orders of magnitude below that region. Two behaviours are plausible:

- **Power law continues**: capability per parameter is flat, and small models are simply worse.
- **Threshold behaviour**: below some size, specific capabilities are absent regardless of data, then
  appear abruptly — which is what `[S34]` suggests for multi-step reasoning.

**These imply opposite strategies.** Under the first, AETHER should maximise `P` and accept narrow
data. Under the second, AETHER should accept a capability ceiling and invest in tooling, memory and
retrieval instead — which is exactly what the six-component split does.

**[OPEN]** AETHER does not know which regime applies, and cannot know without training Config N and
Config M and measuring the difference. **This is the central empirical question of the entire
project**, and it is answerable cheaply: [§6.4](#64-the-cheapest-informative-experiment).

---

## 6. Experimental design for density questions

### 6.1 What a controlled comparison requires

A capability comparison between two configurations is only meaningful if **exactly one axis differs**
and the others are held fixed. AETHER proposes three canonical controlled pairs:

| Pair | Held fixed | Varied | Question |
| --- | --- | --- | --- |
| D1 | `P`, `D`, data, objective | architecture family | Does architecture matter at 8 M? |
| D2 | architecture, `D`, data | `P` (N vs M) | Is there a capability threshold? |
| D3 | architecture, `P`, data | `D` (10 vs 20 tok/param) | Is AETHER data-starved? |

**[PROPOSED]** No result is reported unless it comes from one of these pairs or an explicit ablation
registered in [`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §4.

### 6.2 The comparison table AETHER will be allowed to publish

A Phase 5 result may be reported **only** in this shape:

| Config | `P` | `D` | `F_train` | BPC (held-out) | MMLU | ARC-Easy | `M_peak` | tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Config N | 1,840,256 | *measured* | *measured* | *measured* | *measured* | *measured* | *measured* | *measured* |
| Config M | 8,425,728 | *measured* | *measured* | *measured* | *measured* | *measured* | *measured* | *measured* |

Every cell is a measurement or is marked `not run`. **No cell may contain an estimate in a results
table.** Estimates live in the design documents and are labelled.

### 6.3 Why AETHER will not compare against published models

It is tempting to place AETHER's BPC next to a published small model's. AETHER forbids this in
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §7 because the corpus, tokeniser, preprocessing, evaluation
split and even the metric definition differ. A comparison across those differences measures the
differences, not the models.

The only legitimate cross-model comparison is on a **shared, public, contamination-controlled
benchmark** with a stated protocol — and AETHER will not have the budget to run such a benchmark
properly until Phase 7.

### 6.4 The cheapest informative experiment

If exactly one experiment can be run, it should be **D2** at 5 tokens/parameter: train Config T, N and
M on the same small corpus and plot BPC against `P`. Three runs, hours to days each, and it produces
the first evidence about which regime AETHER is in (`§5.1`). This is why Config T exists
(`ARCHITECTURE_SPEC.md` §5.4).

---

## 7. Multi-task learning and catastrophic forgetting

At AETHER's scale, multi-task training is a **budget** question, not a capability question: every task
added divides the same token budget.

| Claim | Status |
| --- | --- |
| Multi-task training shares representations and can improve data efficiency | **[ESTABLISHED]** in general |
| It holds when total data is fixed and small | **Unknown** — this is the regime that matters here |
| Catastrophic forgetting occurs when task distributions shift | **[ESTABLISHED]** in general |
| AETHER will avoid it by **not** doing sequential fine-tuning | **[PROPOSED]** — a design choice, not a result |

**[PROPOSED]** AETHER's first model trains on a **single mixed corpus in one pass**, never on a
sequence of task-specific stages. Sequential fine-tuning is deferred to Phase 9 if at all, precisely
because forgetting is hardest to detect without a comprehensive evaluation suite — which AETHER will
not have until the same phase.

---

## 8. Distillation: what AETHER may and may not do

AETHER's identity constraint is that the Core is trained **from random initialisation** and does not
adopt another model's pretrained weights or learned representations.

| Form | Permitted? | Reasoning |
| --- | --- | --- |
| Train from another model's weights | **Prohibited** | Violates project identity |
| Distil from another model's outputs | **Prohibited** | Outputs encode learned representations; the Core would inherit them |
| Distil from a **larger AETHER model trained by this project** | **Permitted** | Both models are originally trained by AETHER |
| Distil from **research-generated supervision** (programmatic labels, verified synthetic data) | **Permitted** | The supervision is generated by rules/verification, not by a foreign network |

The permitted third row is genuinely useful and is often overlooked: Config M can teach Config T, and
a larger future AETHER can teach Config M. That is self-distillation within the project's own lineage.

**[OPEN]** Whether "research-generated supervision" includes synthetic data produced by a third-party
model is **unresolved and is a maintainer decision**, not a technical one. The conservative reading —
prohibited — is AETHER's default until decided. `[S39]` describes the mechanism; it does not settle the
policy.

---

## 9. Curriculum and synthetic data

| Approach | Evidence base | AETHER's position |
| --- | --- | --- |
| Sequence-length curriculum (short → long) | Weak but plausible | **[PROPOSED]** — cheap, low risk |
| Difficulty curriculum | Mixed; hard to define difficulty | **Deferred** — requires a difficulty estimator AETHER cannot validate |
| Programmatically verified synthetic data | Strong for narrow tasks | **[PROPOSED]** — Phase 5, for validation tasks only |
| Model-generated synthetic data | Risk of collapse and contamination | **Prohibited** in Phase 5 pending a policy decision |

The strongest available evidence that synthetic, restricted data can produce real capability at small
scale is `[S10]`, which generated stories from a small vocabulary of common words. Its limitation is
the mirror of its strength: the corpus is narrow by construction, so the resulting capability is too.

---

## 10. Unresolved questions

1. Which regime is AETHER in — power law or threshold (§5.1)? **The central question.**
2. Is 10 tokens/parameter starving Config M, or is it near a plateau at this scale? **[OPEN]**
3. Does weight tying measurably hurt BPC at `d = 128`? **[OPEN]**
4. Is the 57 % embedding share of Config N a fatal inefficiency that argues for a smaller vocabulary
   plus a longer context? `TOKENIZER_SPEC.md` §3 argues yes; unmeasured. **[OPEN]**
5. Does multi-task training help or merely divide a fixed budget in AETHER's regime? **[OPEN]**
6. Is self-distillation (M → T) worth the complexity, and does it preserve the from-scratch property in
   a way the project's principles accept? **[OPEN]** — maintainer decision pending
7. Should the four quotients in §2.1 be reported as ratios at all, given §1.1's objections? **Proposed:
   yes, but only alongside the raw row, never instead of it.** **[OPEN]**

---

## 11. Status summary

| Item | Status |
| --- | --- |
| Universal intelligence-density metric | **Refused** — §1.1 |
| Four-quotient measurement matrix | **Proposed** — §2 |
| Parameter accounting of tying and vocabulary | **Exact arithmetic**, no quality evidence |
| Ranking of levers by expected effect | **Speculative**, confidence stated per row |
| Evidence that data distribution beats architecture at small scale | **Moderate** `[S10]`, not AETHER-specific |
| Any measurement of AETHER | **None.** Nothing has been trained or built. |
