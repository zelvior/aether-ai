# AETHER — Evaluation Plan

Status: **Proposal.** No evaluation has been run. **Every number this plan would produce is currently
absent.** This document defines how AETHER will measure itself, what counts as evidence, and what
AETHER is forbidden from claiming.

It is written to satisfy [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md), and where the two
disagree, the research principles win.

---

## 1. Purpose and the baseline problem

AETHER has no baseline. There is no previous AETHER result, no reference AETHER implementation, and no
configuration that "works". Every metric below will be measured for the first time when Phase 7–9 runs.

This creates a specific obligation: **the first measurements are descriptions, not achievements.** A
number like "12 tokens/second" is not good or bad — it is a fact about a machine and a build. Presenting
it as a result would be the exact failure mode [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §7
forbids.

The plan therefore separates three things that are often conflated:

| Kind | Example | What it establishes |
| --- | --- | --- |
| **Characterisation** | "Peak RSS was *N* MiB on machine X" (*N* filled in by the run) | What the system does |
| **Comparison** | "Configuration A used *k* % less memory than B, on this host" | A relative fact, valid only within its conditions |
| **Capability claim** | The model handles task Y | Only with a proper harness, baseline, and reproducibility |

AETHER may publish characterisation freely. It may publish comparisons only with matched conditions.
It may publish capability claims only after Phase 9.

---

## 2. What will be measured

### 2.1 Static properties

| Metric | Unit | Method | Phase |
| --- | --- | --- | --- |
| Parameter count | count | Read from model file metadata **and** independently counted by the loader; the two must agree or the file is rejected | 6 |
| Parameter breakdown | count per tensor type | Reported from the tensor table, not from this document's arithmetic | 6 |
| Model size on disk | bytes | `stat` on the file; reported alongside the declared size | 6 |
| Weight footprint in memory | bytes | Sum of tensor sizes as mapped; **excludes** transient buffers | 6 |
| Quantisation ratio | ratio | `fp32 bytes / int8 bytes`, reported per tensor group | 8 |

**Note on the parameter count.** [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §6 derives 8 425 728
parameters analytically. That number becomes a *fact* only when a built model reports it and the loader
independently confirms it. Until then it is a **derived expectation**, and any document quoting it must
say so.

### 2.2 Runtime memory

| Metric | Unit | Method | Why it matters |
| --- | --- | --- | --- |
| Peak resident set size (RSS) | bytes | OS-level sampling at ≥ 10 Hz across a full run; report **peak**, and **time-weighted mean** separately | RSS is what the process actually holds |
| Peak virtual size (VSZ) | bytes | OS-level sampling | VSZ is what the 32-bit address space actually gives up; a design can fit RSS and fail VSZ |
| Arena allocation total | bytes | Runtime's own accounting, cross-checked against RSS | Catches double-counting and leaks |
| Mapped-but-unused size | bytes | `mmap` length minus resident pages, where available | Distinguishes reserved from used |
| Fragmentation indicator | ratio | Largest successful allocation / total free VA, where measurable | Pre-empts the §[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §7 failure mode |
| Allocation failure behaviour | pass/fail | Constrain the address space (`ulimit -v`) and confirm a clean error, not a crash | Correctness under pressure |

**Peak RSS and peak VSZ are reported together, always.** Reporting one without the other is a form of
misleading (§7).

### 2.3 Performance

Timing metrics are the most abused in this field, so their definitions are normative.

| Metric | Definition | Exclusions |
| --- | --- | --- |
| **Time to first token (TTFT)** | Wall-clock from `generate()` entry to the first output token being available | Excludes model load; a separate **load time** is reported |
| **Decode throughput** | `(tokens generated − 1) / (t_last − t_first)` — steady-state only | Excludes prefill; excludes the first token |
| **Prefill throughput** | `prompt_tokens / prompt_duration` for a fixed prompt length | Reported separately for each prompt length |
| **Tokens/second (aggregate)** | Total tokens / total wall-clock, including prefill | Must state batch size, prompt length, output length |
| **CPU utilisation** | `utime + stime` from `getrusage` divided by wall-clock | Reported as a fraction of one core and the thread count |
| **Load time** | Wall-clock from `open()` to model ready | Cold and warm cache reported separately |
| **Energy** | **Not measured** | No measurement method exists in this project |

**Mandatory conditions to report with every timing number:**

1. CPU model, core count, base/clocks where obtainable
2. RAM amount and speed class
3. OS and kernel version
4. Compiler, version, optimisation flags
5. `FLT_EVAL_METHOD` actually in force ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2.3)
6. Architecture: **32-bit or 64-bit, explicitly**
7. Thread count (including "1")
8. Prompt token count and output token count
9. Cache state: cold or warm, and how it was established
10. Number of repetitions and the aggregation used
11. Whether the machine was otherwise idle

A timing number without these is not publishable in this repository.

### 2.4 Output quality

Deferred to Phase 9, but the framework is fixed now so that Phase 4–6 code can accumulate what Phase 9
needs.

| Category | Metric | Notes |
| --- | --- | --- |
| Language modelling | Bits-per-byte on a held-out split | **Preferred over perplexity** because it is tokenizer-independent and therefore comparable across vocabulary changes |
| Task accuracy | Exact-match / accuracy per task | Only on tasks with determinable answers |
| Generation coherence | Fixed rubric, human or model-graded | Must state the grader; see §6.4 |
| Robustness | Performance on perturbed inputs | Only if a perturbation suite is defined |
| Repetition | Distinct-*n* / repeated-*n*-gram rate | Cheap, and catches a common small-model failure |
| Instruction following | **Not applicable at this scale** | See [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8 |

**Bits-per-byte** is chosen deliberately: models with different vocabularies cannot be compared on
perplexity, and AETHER anticipates changing `V`. Bpb normalises for that.

---

## 3. What will *not* be claimed

Recorded explicitly, because each is a common and tempting error:

| Not claimed | Reason |
| --- | --- |
| Any comparison to a named published model | No matched harness, hardware, or training budget exists |
| "State-of-the-art" anything | No basis for the comparison |
| Tokens/second predictions | Depends on implementation that does not exist (§[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §7.3) |
| 32-bit compatibility | No 32-bit build or run ([`ROADMAP.md`](ROADMAP.md) Phase 7) |
| Energy efficiency | Not measured, no method |
| Quality from the model while it is untrained | An untrained model's output is noise |
| Generality | A narrow model is not a general one ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8) |
| Speedup from quantisation | Would need measurement on a target **with** the relevant instructions |

---

## 4. Baselines

### 4.1 Required baselines

| Baseline | What it is | Why required |
| --- | --- | --- |
| **Random** | Uniform token sampling | Establishes the floor. Any result must beat it or something is wrong |
| **Unigram-frequency** | A model-free sampler matching the training distribution's unigram frequencies | A strong trivial baseline for bpb. Beating "predict the frequent tokens" is harder than it looks |
| **Repeat-back** | Copies the prompt | Exposes evaluation harnesses that reward trivial continuation |

These three cost almost nothing and catch most harness bugs. AETHER requires all three.

### 4.2 Optional reference comparisons

Possible only if the licence permits and the comparison is honest:

- A same-architecture model trained by AETHER at a different size (self-comparison, always fair).
- An external reference implementation measured **on the same machine**, using its own harness, with
  its configuration disclosed. This is a **characterisation** of that implementation here, not a claim
  that AETHER is better than it.

**[PROPOSED]** Never compare AETHER's number to a number copied from a paper. If a paper's number is
cited at all, it must be labelled **cross-paper**, with the setup differences stated, and it must not
appear in a comparison table as if it were measured under the same conditions.

### 4.3 What "better" means

For the first model, "better" means exactly one thing: **measurably better than the unigram-frequency
baseline on held-out bits-per-byte, on a documented corpus, reproduced by two runs.** Nothing more.

Setting a higher bar at this stage would be a claim without an experiment behind it.

---

## 5. 32-bit versus 64-bit comparison protocol

This is the comparison AETHER exists to make possible, and it is the one most likely to be done
dishonestly. The protocol is fixed in advance.

### 5.1 Comparison conditions

Both builds must share, or differences must be stated as confounds:

| Condition | Requirement |
| --- | --- |
| Source revision | **Identical commit** |
| Compiler and version | Identical where a cross-compiler exists; else both reported |
| Optimisation level | Identical |
| Model file | **Byte-identical** — same checksum |
| Input prompts | Identical and committed |
| Thread count | Identical (normally 1) |
| Decoding | Greedy for equivalence; sampling with a fixed seed for throughput |
| Evaluation harness | Identical, same version |

### 5.2 What is compared

| Dimension | Metric | Acceptance |
| --- | --- | --- |
| **Output equivalence** | Max abs difference in logits; token agreement over ≥ 1000 tokens | See §5.3 |
| Peak memory | Peak RSS, peak VSZ per build | Reported, not judged |
| Memory envelope | Does the 32-bit process stay within the 512 MiB working target | Pass/fail |
| Throughput | TTFT, decode tokens/s per build | Reported with full conditions |
| Failure behaviour | Behaviour under memory pressure | Clean error required |
| Allocation | Largest successful allocation per build | Reported |

### 5.3 Equivalence tolerance

**[PROPOSED]** The two builds are "equivalent within tolerance" if:

1. Max absolute logit difference ≤ `1e-3` relative to the logit scale, **or** ≤ `1e-4` absolute,
   whichever is larger; **and**
2. Greedy token agreement ≥ 99 % over ≥ 1000 generated tokens on fixed prompts; **and**
3. No NaN, inf, or uninitialised-memory dependence in either build.

Any disagreement beyond this is a **finding to be reported**, not a failure to be hidden. It may be
expected on x87 ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2); if so, the x87 path's tolerances
are reported separately and the reason explained.

**[PROPOSED]** Assertions of exact bit-equality between 32- and 64-bit builds are **false and
forbidden**. A system using transcendental functions across different FPU evaluation models cannot
achieve it generally, and claiming it would be a fabricated result.

#### Scope: this tolerance covers arithmetic, not representation

The `1e-3` figure above is calibrated for **identical weights, different floating-point evaluation** —
the x87-versus-SSE2 question. It does **not** extend to comparisons where the weights themselves differ.

`NUMERICAL_STRATEGY.md` §9A shows int8-quantised weights reconstruct with ≈ 0.0074 relative error per
matrix, compounding to **≈ 0.021 across 8 layers** — twenty times the tolerance above, with everything
working as intended.

| Comparison | Applies §5.3? |
| --- | --- |
| fp32 x87 vs fp32 SSE2 | **Yes** |
| fp32 vs int8 | **No** — needs its own tolerance, derived in Phase 8 |

**[OPEN]** The int8 tolerance and its acceptable BPC degradation must both be **pre-registered before
the first quantised comparison**, per [`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §4.1.
Choosing them after seeing the numbers would make the result unfalsifiable.

---

## 6. Methodology details that are easy to get wrong

### 6.1 Warm-up and cold cache

Report **both**, labelled. A "cold" run is defined as: first execution after boot, model file not in
page cache. This is verified, not assumed — if verification is impossible, the run is reported as
"warm" by default, because that is the conservative label for a performance claim.

### 6.2 Repetitions

- **≥ 5 repetitions** per configuration for any timing metric.
- Report **median and full range**. Not mean alone.
- Discard nothing. If a run is an outlier, it is reported and explained, not removed.

### 6.3 Measurement overhead

Timing must not change the thing timed. Where sampling RSS changes scheduling, that is stated. The
sampling interval is reported.

### 6.4 Graded evaluation

If any metric requires a judge (human or model-graded):

- The **exact judge**, version, and prompt are published.
- A sample of judgements is published with the items.
- The judge's own error rate is acknowledged as unmeasured unless measured.
- AETHER does not present an LLM-graded score as an objective measurement
  ([`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §3).

### 6.5 Blinding

For any comparison between two AETHER configurations, the person or process scoring outputs should not
know which configuration produced which output. Where blinding is impossible, that is stated.

---

## 7. Forbidden comparisons

Concrete, so there is no ambiguity later. AETHER will not:

1. Compare models of **different parameter counts** and attribute the difference to design.
2. Compare runs on **different hardware** and present it as efficiency.
3. Quote a **paper's number** in a comparison table with an AETHER measurement.
4. Report **throughput without input/output lengths and thread count**.
5. Report **memory without distinguishing RSS, VSZ, weights, and peak**.
6. Put **quantised and unquantised results** in the same column without labelling.
7. Claim **32-bit support** from a 64-bit build, or from a build that never ran.
8. Report **"up to N×"** as if it were typical.
9. Present **one favourable seed** as the result.
10. Use **perplexity** to compare models with different tokenizers.
11. Report a **greedy-decoded single sample** as evidence of capability.
12. Compare against a **baseline run under different conditions** without stating them.
13. Claim **energy efficiency** without measurement.
14. Present a **derived expectation** (e.g. §2.1's parameter count) as a measurement.

---

## 8. Reporting template

Every evaluation report follows this structure. A report missing a section is incomplete, and is
labelled as such rather than published.

```
1. Question          — what this run tests, in one sentence
2. Hypothesis        — expected outcome and falsification condition
3. Configuration     — commit, model checksum, tokenizer version, hyperparameters
4. Environment       — all 11 mandatory conditions (§2.3)
5. Commands          — exact invocation, copy-pasteable
6. Raw results       — every repetition, not just the aggregate
7. Statistics        — median, range, n
8. Comparison        — against stated baselines only (§4)
9. What this shows    — bounded interpretation
10. What this does not show — explicitly
11. Anomalies        — anything unexplained, including outliers
12. Reproduction     — status: independent / author-only / not reproduced
```

Section 10 is **mandatory and must not be empty.** An evaluation that shows something and does not
bound it is not a research result, it is marketing.

---

## 9. Reproducibility status

Per [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §1, each report carries one of:

| Status | Meaning |
| --- | --- |
| **Reproduced independently** | Someone other than the author obtained comparable results from the published commands |
| **Reproduced by author only** | The author re-ran and got comparable results; nobody else has |
| **Not reproduced** | A single run. Permitted, but must be labelled |

**[PROPOSED]** No AETHER result may be described as "verified" unless it is in the first category.

---

## 10. Tooling requirements (Phase 6–9)

None of this exists. Recorded so it is built once, not ad hoc.

| Tool | Requirement |
| --- | --- |
| Timing harness | Reports all 11 conditions; refuses to emit a result without them |
| Memory sampler | RSS and VSZ at a fixed interval, machine-readable output |
| Equivalence checker | Compares two builds' logits and token streams per §5.3 |
| Baseline sampler | Random, unigram-frequency, repeat-back (§4.1) |
| bpb calculator | Tokenizer-independent, with the tokenizer reported for context |
| Report generator | Fills the §8 template; fails if section 10 is empty |
| Result store | Plain-text, version-controlled, with the model checksum |

The **report generator failing when section 10 is empty** is a deliberate forcing function.

---

## 11. Unresolved questions

1. What hardware is representative of the 32-bit target population? Any single machine is a sample of
   one, and results on it generalise weakly. **[OPEN]** — Phase 7.
2. Is `1e-3` the right equivalence tolerance for the x87 path, or is it too tight to ever pass?
   **[OPEN]**
3. Which corpus provides held-out bpb, and is its licence compatible with publishing derived metrics?
   Under [`DATA_POLICY.md`](DATA_POLICY.md) a manifest is required **before** any run. **[OPEN]**
4. Is a task-accuracy suite meaningful for a model this small, or is bpb the only honest metric?
   **Proposed: bpb plus repetition rate**, with task accuracy deferred. **[OPEN]**
5. Does any measurement of energy use fall within scope? **Proposed: no**, and therefore no energy
   claim of any kind is made. **[OPEN]**
6. How should results be archived so they remain findable in a year? Plain text in the repository, one
   file per report, named by date and commit. **[OPEN]** — convention not yet fixed.
