# AETHER — Experimental Methodology

Status: **Method specification.** No experiment has been run. This document defines what would make an
AETHER claim admissible, so that the first claim cannot be made carelessly.

Related: [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) (what is measured) ·
[`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) (how runs are produced) ·
[`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) (governing policy) ·
[`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §6 (what comparisons are allowed)

---

## 1. The admissibility rule

> **A result is admissible only if a third party could re-run it from the recorded artefacts and obtain
> a comparable result within a stated tolerance.**

Everything below exists to make that true. A number without an artefact is an anecdote.

### 1.1 The five admissibility conditions

| # | Condition | Fails if |
| --- | --- | --- |
| **A1** | Configuration fully recorded | Any hyperparameter was a default not written down |
| **A2** | Data versioned and hashed | The corpus changed between runs |
| **A3** | Evaluation held out and uncontaminated | Any eval item appeared in training |
| **A4** | Comparison controlled | More than one axis varied |
| **A5** | Uncertainty reported | A single run is presented as a point estimate |

**[PROPOSED]** All five are required. Four out of five is not a result.

---

## 2. Run manifests

Every run emits one manifest. Fields, not prose:

| Group | Fields |
| --- | --- |
| Identity | run id, start/end UTC, operator, git commit |
| Model | config name, `V`, `d`, `L`, `H`, `d_ff`, `W`, `T_train`, `T_max`, parameter count |
| Init | scheme, seed, per-tensor seed derivation rule |
| Optimiser | name, `β₁`, `β₂`, `ε`, weight decay, clipping, LR schedule, peak LR, warm-up |
| Batch | micro-batch, accumulation, effective tokens, sequence length |
| Data | corpus id, content hash, token count, dedup settings, filter settings, language mix |
| Tokeniser | version, vocab hash, merge-list hash |
| Environment | OS, arch, compiler + version, flags, thread count |
| Numerics | dtype, accumulation order policy, `-ffloat-store` on/off |
| Outcome | final loss, best val loss, wall time, peak RSS, peak virtual, tokens/s |
| Artefacts | checkpoint hashes, log hash, output sample hash |

**[PROPOSED]** The manifest is **machine-generated**, never hand-edited. A hand-edited manifest is not
evidence.

### 2.1 Why the numerics fields exist

Most ML experiment tracking omits them. AETHER cannot: `-ffloat-store` changes results on x87, and
without recording it, two runs that disagree cannot be diagnosed
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2).

---

## 3. Seeds and determinism

| Source | Control |
| --- | --- |
| Weight initialisation | One master seed |
| Data shuffling | Derived stream, not shared |
| Batch order | Derived from `(seed, epoch, index)` |
| Dropout | **Absent** by design ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §8A.5) |
| Thread count | 1 |

**Derived streams matter.** Using one RNG for both init and shuffling couples them: changing the shuffle
changes the initialisation, and an observed difference cannot be attributed. AETHER derives independent,
named streams from the master seed.

### 3.1 What determinism AETHER promises

| Scope | Promise |
| --- | --- |
| Same build, same machine, same seed | **Identical** loss curve |
| Different machine, same architecture | Comparable within tolerance |
| Different compiler version | Comparable within tolerance |
| GPU vs CPU | Not applicable — no GPU path exists |

---

## 4. Ablation protocol

An ablation is admissible only if it changes **exactly one** thing.

| Rule | Detail |
| --- | --- |
| One variable | Two changes ⇒ a new experiment, not an ablation |
| Registered in advance | The hypothesis is written before the run |
| Same data | Unless the ablation *is* the data |
| Same budget | Comparisons at equal tokens, unless FLOPs are the variable |
| Reported whether positive or negative | **No selective reporting** |

### 4.1 The pre-registration rule

**[PROPOSED]** Before a run, a one-paragraph record states: what is being changed, what is expected, and
what outcome would falsify the expectation. This is cheap and it is the only defence against
interpreting a noisy curve after the fact.

It also makes negative results publishable, which is the point
([`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §9).

---

## 5. Statistical reporting

At AETHER's budget, most experiments are `n = 1` runs. That is a real constraint and it must be handled
honestly rather than hidden.

| Situation | Required reporting |
| --- | --- |
| Single run | State `n = 1`. **Do not** report a confidence interval from one run |
| Multiple seeds | Report mean and standard deviation; state `n` |
| Curve comparison | Report the full curve, not the final point |
| Difference smaller than seed variance | **Report as indistinguishable**, not as an improvement |

### 5.1 Estimating seed variance is itself expensive

Three seeds at Config M is roughly three weeks of compute
([`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §7). AETHER therefore proposes to estimate seed
variance **at Config N and Config T**, where it is affordable, and to state explicitly that Config M
results carry **unmeasured** variance.

That is a limitation, and it is the honest one: reporting a Config M number without a variance estimate
is legitimate *provided the omission is stated*.

---

## 6. Contamination control

`[S42]` finds train–test overlap affecting over 4 % of a standard validation set. At AETHER's data scale,
a leaked evaluation item is not a rounding error — it can be a meaningful fraction of a small eval set.

| Control | Rule |
| --- | --- |
| Eval sets held out before dedup | Yes |
| Exact substring overlap | **Zero tolerance** — a run with overlap is void |
| Near-duplicate overlap | Checked with the same dedup tooling |
| Benchmark tuning | **Forbidden** — no eval-guided hyperparameter selection on reported sets |
| Reporting | State which sets were never touched |

The fourth row is the one most often violated in practice: adjusting a hyperparameter because eval went
down is training on eval, regardless of intent.

---

## 7. Comparing configurations

Permitted comparisons, from [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §6:

| Comparison | Held fixed | Varied |
| --- | --- | --- |
| D1 architecture | `P`, `D`, data, objective | family |
| D2 scale | architecture, `D`, data | `P` |
| D3 data | architecture, `P`, data | `D` |

**Forbidden:** comparing AETHER against a published model's number. The corpus, tokeniser, preprocessing,
split and metric definition all differ, so such a comparison measures the differences.

---

## 8. Recording negative results

| Requirement | Statement |
| --- | --- |
| `X-1` | Every registered experiment is recorded whether or not it succeeded |
| `X-2` | A failed run records *why* it failed |
| `X-3` | A hypothesis falsified is recorded as falsified |

This is a process commitment, not a technical control, and it is the one most often abandoned under
time pressure. Stating it makes the abandonment visible.

---

## 9. The minimum publishable experiment

Before any capability claim, this sequence must complete:

| Step | Produces | Blocks |
| --- | --- | --- |
| 1. Config T trains on a synthetic task | A loss curve | Everything |
| 2. Config T round-trips through AMC | A loadable model file | Runtime work |
| 3. 32-bit output matches 64-bit | Equivalence report | Any portability claim |
| 4. Config N trains on real data | BPC number | Any capability claim |
| 5. Seeds at Config N | Variance estimate | Interpreting step 4 |

**[PROPOSED]** Steps 1–3 are cheap and answer "does the machinery work?". Step 4 answers "does it
learn?". Step 5 answers "is the answer in step 4 real?".

---

## 10. Failure modes this methodology is designed to catch

| Failure | Caught by |
| --- | --- |
| Contaminated eval inflating results | §6 zero-tolerance overlap |
| A change attributed to the wrong variable | §4 one-variable rule |
| Run reported as a win without variance | §5.1 `n = 1` disclosure |
| Hyperparameters quietly tuned on eval | §6 forbidden-tuning rule |
| Reproducibility failure discovered late | §2 manifests, §9 step 2 |
| A negative result disappearing | §8 |

---

## 11. Unresolved questions

1. What tolerance defines "comparable" for a cross-machine re-run? **Proposed: the
   `EVALUATION_PLAN.md` §5 tolerances apply to outputs, and losses must agree to 3 significant figures
   on a fixed checkpoint.** **[OPEN]**
2. How many seeds are affordable at Config N to estimate variance? **[OPEN]**
3. Should manifests be schema-validated in CI? **Proposed: yes once a manifest exists.** **[OPEN]**
4. Is pre-registration enforceable in a single-maintainer project, or only aspirational? **[OPEN]**
5. Should negative results live in the repo or in release notes? **[OPEN]**

---

## 12. Status summary

| Item | Status |
| --- | --- |
| Admissibility rule | **Defined**, five conditions |
| Run manifests | **Specified**, ~40 fields, machine-generated |
| Seed derivation | **Specified** — independent named streams |
| Ablation protocol | **Specified** — one variable, pre-registered |
| Statistical reporting | **Specified** — `n = 1` must be disclosed |
| Contamination control | **Specified** — zero tolerance |
| Negative-result recording | **Committed** |
| Any experiment conducted | **None.** |
