# AETHER — Phase 2 Findings

Status: **Synthesis of Phase 2.** No result in this document is a measurement. Every figure is a
derivation, a simulation, or a literature finding, and each is labelled in the body.

This is the retrospective: what Phase 2 actually established, what it disproved, what it got wrong, and
what it cannot know. The individual specifications carry the detail; this document carries the
conclusions.

---

## 1. What Phase 2 set out to answer

The brief posed one question:

> **How much useful, reliable and generalizable intelligence can an independently developed AI system
> achieve when every parameter, byte of memory and computational operation matters?**

Phase 2 was required to answer it as research, not as assertion, and to refuse to promise capability it
could not demonstrate. It has **not answered the question** — that requires training a model
([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md)). It has done three other things:

1. Established the constraints as **quantities** rather than adjectives.
2. Found and corrected **six substantive errors** in the project's own reasoning.
3. Identified that the central question is **cheap to answer** (≈ 5 days of compute), which is the single
   most actionable outcome of the phase.

---

## 2. The nine findings that changed the design

Each of these was discovered *during* Phase 2 and each changed something concrete.

### 2.1 SwiGLU parameter accounting was wrong by 50 % per layer

An earlier draft used `2·d·d_ff` for the SwiGLU block. The block has a `d × 2·d_ff` gate/up projection
and a `d_ff × d` down projection, giving **`3·d·d_ff`**. Recomputing raised every parameter count and
forced `d_ff` from 1024 → 688 (Config M) and 512 → 344 (Config N) to preserve parity with a 4× ReLU MLP.

**Class of error:** a formula that is internally consistent with every number derived from it, and
nevertheless describes the wrong matrix shapes. Only reconciliation against the shapes caught it.

### 2.2 The windowed configuration could not see its own context (Config T)

Sliding-window causal attention has a receptive field of `L·(W−1)+1`. Config T was proposed with
`W = 64, L = 2` → **127 tokens**, against a declared `T_max = 256` — **49.6 % coverage**. Half the
declared context was structurally unreachable, and no parameter or memory check would have revealed it.

Fixed to `W = 128` at **zero parameter cost**. The invariant is now asserted mechanically.

### 2.3 A reachable zero-byte allocation on the 32-bit target

From AETHER's own Config M dimensions: the full attention score buffer at `T_max = 8192, H = 8, b = 8` is

```
8 × 8 × 8192 × 8192 × 4 = 17,179,869,184  ≡  0  (mod 2³²)
```

An unchecked 32-bit size computation yields a **successful zero-byte allocation followed by an
out-of-bounds write**. This is not hypothetical — it is what the declared dimensions produce. It
became error code `E_OVERFLOW` and a mandatory 64-bit-then-narrow discipline.

### 2.4 Quantisation error is ~1,370× the arithmetic error, and the rules did not cover it

`NUMERICAL_STRATEGY` §9 bounds `binary32` arithmetic error. Simulating int8 weight reconstruction at
Config M's real shapes gives ≈ 0.0074 relative per matrix, compounding to **≈ 0.021 across 8 layers**.

| Error source | Magnitude |
| --- | --- |
| `binary32` arithmetic, head (`V=8192`) | 4.89 × 10⁻⁴ |
| **int8 weights, 8 layers** | **≈ 2.1 × 10⁻²** |

The existing equivalence tolerance of `1e-3` would classify a **correctly working** int8 model as a
failure. A second, separately derived tolerance is now required and is explicitly unset.

### 2.5 32-bit *training* is infeasible, and that was being quietly assumed

Config M at 10 tokens/parameter needs ≈ 4.26 × 10¹⁵ FLOPs. At a plausible 1 GFLOP/s on a 32-bit core
that is **≈ 49 days**; at the optimistic 10 GFLOP/s, ≈ 5 days — but 10 GFLOP/s on a 32-bit CPU is not
attainable ([`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §3.3).

32-bit training is now an explicit non-goal (`N-T1`). Training runs on x86-64; 32-bit remains the
**inference** target, which is what the project's principles actually require.

### 2.6 The six-component ecosystem is unjustified if the Core is strong

[`ECOSYSTEM_ARCHITECTURE.md`](ECOSYSTEM_ARCHITECTURE.md) §4 states a conditional the documentation had
previously hidden: three of the five subsystems exist because an 8 M-parameter model cannot do exact
arithmetic, hold world knowledge, or remember across sessions. **If Config M turns out to be capable, a
two-component design (Core + retrieval) is the better engineering choice.**

This is registered with an ablation design ([`ECOSYSTEM_ARCHITECTURE.md`](ECOSYSTEM_ARCHITECTURE.md)
§8A) that would detect it.

### 2.7 SwiGLU **compute** was undercounted by 50 % per layer

Finding 2.1 corrected SwiGLU *parameters*. The same block's *compute* was still charged as
`2·T·d·d_ff` — treating the fused `d × 2·d_ff` gate/up weight as one matrix applied once. Fusing the
weights does not fuse the arithmetic: gate and up are two independent projections, each `d·d_ff` MACs,
and the down projection is a third. The correct charge is `3·T·d·d_ff`.

Undercounting every forward, backward and FLOPs figure by **28.7 %** of the layer. Config M prefill moves
from 7.987 → **9.430 GFLOP**; decode from 16.12 → **18.94 MFLOP/token**.

**Class of error:** the *same* block, the *same* confusion, missed a second time — because the parameter
formula had been fixed and the compute formula was never re-checked against it. A `3:2` ratio was even
written down as an insight, when the truth is `1:1`. What caught it was asserting that the backward pass
equals exactly `2×` forward, then comparing the result against `6ND`.

### 2.8 Nine cited sources were never registered

`[S11]`–`[S19]` — the BPE, unigram, SentencePiece, GPT-2, LLM.int8, GPTQ, SmoothQuant, AWQ and BitNet
papers — were cited in **60+ places** across three documents and had **no entry in
`RESEARCH_REFERENCES.md`**. The registry said `[S1]`–`[S28]` were established; nine of them were not.

All nine now carry full eight-field annotations verified against arXiv. The registry grows from 40 to
**49 entries**, with **0 undefined and 0 orphaned** citations, and `phase2_calc.py --check` now enforces
that invariant — a deliberately injected non-existent key was confirmed to fail the build.

**Class of error:** a document asserting its own completeness. Nothing compared the cited set against
the defined set, in either direction.

### 2.9 `6ND` is not a constant — it is a 9 % error here and a 3× error at long context

Deriving `6ND` (§5 of [`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md)) made it possible to
check it. It is not exact:

```
exact = 2ND + attention matmuls − 2 × (norm parameters) × T
```

At `T = 512` the two corrections nearly cancel and `6ND` is **9.3 % low**. At `T = 8192` the attention
term dominates and `6ND` is **3.0× low**. Since every published scaling-law compute axis is
`6ND`-based, **published compute-optimal recipes are systematically optimistic for long-context
training** — a caveat that applies to `[S9]` itself.

The identity is asserted for all three configs in `flops_vs_6nd()`.

---

## 3. What is now specified

Twenty-seven documents, ≈ 11 700 lines. Grouped by what they constrain:

| Group | Documents | Constrains |
| --- | --- | --- |
| Core research | `RESEARCH_SURVEY`, `INTELLIGENCE_DENSITY_RESEARCH`, `ARCHITECTURE_SPEC`, `ADAPTIVE_COMPUTATION`, `ECOSYSTEM_ARCHITECTURE` | What the model is and why |
| Mathematics | `MATHEMATICAL_FOUNDATIONS`, `OPTIMISATION_THEORY`, `SCALING_LAW_ANALYSIS` | The derivations behind every figure, and their limits |
| Neural infrastructure | `TRAINING_STRATEGY`, `TOKENIZER_SPEC`, `MULTILINGUAL_RESEARCH`, `NUMERICAL_STRATEGY`, `MODEL_FORMAT_SPEC` | How it is built and stored |
| Ecosystem | `COGNITIVE_SYSTEM_SPEC`, `MEMORY_SYSTEM_SPEC`, `TOOLS_SYSTEM_SPEC`, `KNOWLEDGE_SYSTEM_SPEC`, `RUNTIME_SPEC` | What surrounds it |
| Hardware | `MEMORY_BUDGET`, `CPU_32BIT_RESEARCH`, `PLATFORM_COMPATIBILITY_PLAN` | What it can run on |
| Evaluation | `EVALUATION_PLAN`, `EXPERIMENTAL_METHODOLOGY`, `EXPERIMENT_PLAN` | How claims are earned |
| Reference | `RESEARCH_REFERENCES` | What is cited, and what each source does not show |
| Feasibility | `TRAINING_FEASIBILITY` | What the compute actually costs |

### 3.1 The numbers

| Quantity | Value | Status |
| --- | --- | --- |
| Config M parameters | 8,425,728 | **Derived** |
| Config N parameters | 1,840,256 | **Derived** |
| Config T parameters | 228,672 | **Derived** |
| Config M peak inference | 99.55 MiB | **Derived** |
| Full system (all subsystems) | ≈ 228.55 MiB | **Derived** |
| Config M prefill, `T=512` | 9.430 GFLOP | **Derived** |
| Config M decode | 18.94 MFLOP/token | **Derived** |
| Receptive-field coverage | 99.4–99.7 % | **Derived** |
| int8 error, 8 layers | ≈ 0.021 | **Simulated** |
| Regime-test programme | ≈ 5.3 days @10 GFLOP/s | **Derived from priors** |
| **Anything measured** | **nothing** | — |

---

## 4. What Phase 2 could not establish, and says so

| Question | Why it remains open |
| --- | --- |
| Does the model learn anything useful? | No model exists |
| Power-law or threshold regime? | **`EXPERIMENT_PLAN` E1** — 3.4 days away |
| Is 8.4 M parameters enough for any capability? | Unmeasured; `[S10]` suggests narrow fluency only |
| Does AETHER run on 32-bit? | no build exists; **no claim made** |
| Is BM25 adequate, or is dense retrieval required? | No corpus, no queries |
| Can Urdu/Roman Urdu capability be reached at all? | Data may not exist |
| Is the six-component split right? | Contingent on E1 |
| Is the int8 tolerance acceptable? | Must be measured in Phase 8 |

**Nine of these are cheap to resolve and one — data availability — may not be resolvable at all.**

---

## 5. The most important number in Phase 2

> **The programme that determines whether AETHER's entire strategy is correct costs about 5 days of
> compute — less than a single Config M training run.**

| Experiment | Answers | Cost @10 GFLOP/s |
| --- | --- | --- |
| E1 regime test | Does scale help? | 3.4 d |
| E2 seed variance | How much is noise? | 0.8 d |
| E3 data scaling | Is data the limit? | 1.1 d |
| **Total** | | **≈ 5.3 d** |

This inverts the usual research-project risk. Most projects spend years building before discovering
whether their premise holds. AETHER can test its premise in a week — **once six prerequisites exist**,
none of which currently does.

---

## 6. Where Phase 2 is weakest

Stated because a synthesis that lists only strengths is not a synthesis.

| # | Weakness | Severity |
| --- | --- | --- |
| 1 | **No corpus.** Every training figure assumes data that does not exist and may not be obtainable | **Critical** |
| 2 | **Nothing measured.** All 100 `[PROPOSED]` markers rest on derivation, not observation | High |
| 3 | **Throughput priors are guesses.** The 5-day figure could be 15 days or 2 | High |
| 4 | **Scale extrapolation.** `[S9]`, `[S27]`, `[S34]` were all fitted far above 8 M parameters | High |
| 5 | **Multilingual allocation is untested.** The merge quotas have no empirical basis | Medium |
| 6 | **One `[UNVERIFIED]` in the whole set** — suspiciously few, and probably too few | Medium |
| 7 | **`[OPEN]` count is 184** — the phase is a plan with many loose ends, by construction | Expected |

Weakness 6 deserves emphasis: after 184 open questions, having exactly one `[UNVERIFIED]` marker suggests
the vocabulary of uncertainty in these documents is not fine-grained enough. Many `[OPEN]` items are
really *untested beliefs*, which is a different and stronger claim.

---

## 7. Phase 2's own errors, recorded

Phase 2 corrected its own work six times (§2), and additionally caught two wrong arXiv identifiers during
citation verification:

| Claimed | Actually |
| --- | --- |
| `1608.04016` = SGDR | A Curry compiler; SGDR is `1608.03983` |
| `1804.02767` = an ELMo reference | YOLOv3 |

Both were replaced with verified identifiers before use, and the errors are recorded in
[`RESEARCH_REFERENCES.md`](RESEARCH_REFERENCES.md) §12 rather than quietly fixed. **A documentation set
that records its own citation errors is more trustworthy than one that appears never to have made any.**

---

## 8. What Phase 3 should do, and what it should not

| Should | Should not |
| --- | --- |
| Build the tokenizer and prove `decode(encode(s)) == s` on all four languages | Train anything |
| Measure compression per script on real text | Tune merge quotas without a corpus |
| Assemble a corpus with provenance — **the critical path** | Report any capability |
| Implement Config T forward pass against a hand-checked reference | Make any 32-bit claim |

**[PROPOSED]** The corpus work should start **now**, in parallel with engineering, because
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §8 and [`MULTILINGUAL_RESEARCH.md`](MULTILINGUAL_RESEARCH.md)
§8 both identify data availability — not architecture — as the likely project-limiting constraint.

---

## 9. The honest summary

AETHER now has a **technically defensible plan to test a technically defensible idea**, at a scale
nobody expects to work, on hardware nobody uses.

What is established is that the constraints are real and quantified: 8.4 M parameters, 99.55 MiB of
inference memory, no 32-bit build, no training data. What is not established is whether any of it
produces a useful model.

**The project's integrity now rests on one thing: running E1 before making any claim about capability.**
Everything else in these 10 000 lines is preparation.

---

## 10. Status summary

| Item | Status |
| --- | --- |
| Question posed | **Answered with a plan, not a result** |
| Constraints quantified | **Yes** — every one has a number |
| Design errors found and fixed | **6** |
| Citation errors caught | **2** |
| Documents delivered | **22** (19 required + 3 supporting) |
| Citations verified | **49** |
| Measurements made | **0** |
| Compatibility claims earned | **0** |
| Central question costed | **≈ 5.3 days of compute** |
| Ready for Phase 3 | **Yes, for the tokenizer only** |
