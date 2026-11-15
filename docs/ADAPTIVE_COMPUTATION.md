# AETHER — Adaptive Computation

Status: **Design proposal and literature analysis.** No controller has been implemented or measured. No
configuration in AETHER currently performs adaptive computation.

Related: [`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) (orchestration) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) (the fixed-depth Core) ·
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) (how any benefit would be measured) ·
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) (the envelope the controller must fit inside)

---

## 1. The premise, and why it deserves scrutiny

The intuition is simple: a hard question deserves more computation than an easy one, so a system that
can spend compute where it matters should beat one that cannot.

The intuition is also **partly wrong**, and the literature says so more clearly than this document
could have guessed before reviewing it.

### 1.1 The uncomfortable evidence

| Study | Setting | Result |
| --- | --- | --- |
| `[S29]` ACT | RNN, synthetic algorithmic tasks | **Large gains** |
| `[S29]` ACT | RNN, character-level LM (Hutter Prize) | "ACT does not yield large gains in performance" |
| `[S30]` PonderNet | Synthetic reasoning, QA | **Large gains**, better extrapolation |
| `[S31]` MoE | LSTM LM + MT, clusters | Capacity gain, **not** a memory gain |
| `[S34]` CoT | 540 B LLM | Large gains, **emergent at scale** |

The pattern is consistent and inconvenient: **adaptive computation shows large gains on tasks
constructed to reward it (algorithmic puzzles, variable-difficulty reasoning), and small or absent gains
on language modelling** — which is AETHER's actual workload.

### 1.2 The conclusion AETHER draws

AETHER should not build adaptive computation into the **Core**. It should build it **around** the Core,
as external orchestration, where its costs are visible, its termination is provable, and it can be
measured and switched off.

That is a weaker claim than "adaptive computation is the answer", and it is the one the evidence
supports. `COGNITIVE_SYSTEM_SPEC.md` §4 develops the controller; this document establishes why the
Core stays fixed-depth.

---

## 2. Learned halting: ACT and PonderNet

### 2.1 ACT

`[S29]` adds a per-step halting unit `h_t` and a cumulative probability mass:

```
p_t = sigmoid(W_h · s_t + b_h)              halt probability at step t
N(t) = min{ n : Σ_{i=1..n} p_i ≥ 1 − ε }    number of steps actually taken (stop-gradient)
```

The output is a weighted average of intermediate states, and a **ponder cost** `τ · N(t)` is added to
the loss to discourage computation.

Two properties matter for AETHER:

- **`N(t)` uses a stop-gradient**, so the halting decision is not differentiated — it is a
  thresholded quantity, not a smooth one. This makes it deterministic but non-differentiable, which
  complicates both training and reproducibility analysis.
- **`τ` has no principled value.** It trades loss against compute, and the trade is exactly the thing
  a resource-constrained project most needs to get right.

### 2.2 PonderNet

`[S30]` replaces the thresholded halting with a geometric stopping distribution trained by maximum
likelihood, removing the stop-gradient and improving the objective's behaviour. Reported gains over
ACT are substantial on synthetic tasks.

### 2.3 Why neither is proposed for the Core

| Reason | Detail |
| --- | --- |
| Evidence is on the wrong workload | §1.1 — the LM result is the one that applies |
| Adds a training hyperparameter with no principled setting | `τ` in ACT |
| Breaks the fixed-depth assumption the format and runtime rely on | `MODEL_FORMAT_SPEC.md` §4 encodes `n_layers`; variable depth would need a new field and new validation |
| Interacts badly with `binary32` determinism | Halting depends on a sigmoid crossing a threshold; `NUMERICAL_STRATEGY.md` §9 shows logit errors of `~1e-4` are possible, which can flip a near-threshold halt decision |

That last point is AETHER-specific and is not discussed in either paper. A halt decision near `ε` is a
**discrete** branch on a **continuous** quantity, and AETHER's numerics make such branches
unreliable — the same class of problem as top-1 token disagreement
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9.4).

---

## 3. Chain-of-thought and explicit reasoning traces

`[S34]` shows that eliciting intermediate steps improves reasoning, and — crucially — that the effect
**emerges in sufficiently large models**. The paper's own framing is that the ability appears with
scale, not that it can be induced in any model.

For AETHER this means:

- Proposing chain-of-thought as a Config M capability would be **claiming an emergent ability that the
  cited evidence attributes to models four to five orders of magnitude larger.**
- What AETHER *can* do is emit intermediate tokens if trained to, and **measure** whether it helps.
  That is an experiment, not a design commitment.

**[PROPOSED]** AETHER treats "does an explicit reasoning trace help at 8 M parameters?" as an open
experiment for Phase 5, with the prior expectation that it **does not**. Recording the prior is what
makes a negative result informative.

---

## 4. Mixture of experts and conditional routing

`[S31]` established that sparse expert routing increases capacity without proportional compute. It is
the most successful conditional-computation idea in the literature, and AETHER rejects it — but for a
reason that has nothing to do with compute.

### 4.1 The resource AETHER is short of is not FLOPs

Sparse MoE saves compute. It does **not** save memory: every expert's weights must be resident (or
paged from disk, destroying latency). At Config M, `MEMORY_BUDGET.md` §5 gives a peak inference
footprint of 99.55 MiB against a 512 MiB working target, of which 32.14 MiB is weights. Replacing the
4,227,072-parameter dense MLP with 8 experts of the same size gives:

| | Parameters | Weight storage | Approx. peak |
| --- | --- | --- | --- |
| Config M (dense) | 8,425,728 | 32.14 MiB | 99.55 MiB |
| 8-expert MoE | 38,015,232 | 145.02 MiB | **212.4 MiB** |

That is **41 % of the 512 MiB working target consumed before any context**, for a model whose active
FLOPs are identical. It would still fit inside the 2 GiB envelope (10.4 %), so this is not a
correctness objection — it is a statement that MoE spends the resource AETHER is short of in order to
save the one it is not.

**MoE optimises the resource AETHER has, and spends the resource AETHER lacks.** That is a clean
reason to decline it, and it is worth stating because the opposite conclusion is common.

### 4.2 What AETHER does instead

A single dense MLP with all parameters active on every token. Wasteful of FLOPs by MoE standards;
correct for a machine whose binding constraint is bytes.

---

## 5. Early exiting and confidence

### 5.1 Early exit

An early-exit architecture attaches classifiers to intermediate layers and stops when a confidence
threshold is met. Costs: extra parameters for the exit heads, a threshold to tune, and — critically for
AETHER — **nondeterministic output paths** depending on a continuous quantity crossing a threshold.

### 5.2 What AETHER can measure about confidence, and what it cannot

Token-level confidence is available for free: the softmax distribution. Whether it is *calibrated* is a
different question.

| Source of confidence | Cost | Calibration |
| --- | --- | --- |
| Max softmax probability | 0 — already computed | **Known to be overconfident** for neural LMs |
| Predictive entropy | One pass over `V` | Better, still not calibrated |
| Ensemble disagreement `[S48]` | `k×` storage and compute | Well calibrated |
| Verifier / second pass | `2×` compute or an extra model | Depends entirely on the verifier |

**[ESTABLISHED]** `[S48]` shows deep ensembles give good calibration.
**[PROPOSED, NOT MEASURED]** AETHER cannot afford an ensemble: `k` copies multiply the 32.14 MiB
storage and the 99.55 MiB peak by `k`.

| `k` | Peak inference | % of 2 GiB | % of 512 MiB target |
| --- | --- | --- | --- |
| 1 | 99.55 MiB | 4.9 % | 19.4 % |
| 2 | 199.1 MiB | 9.7 % | 39 % |
| 3 | 298.6 MiB | 14.6 % | **58 %** |

At `k = 3` the ensemble consumes 58 % of the working target before context, and every token costs `3×`
the FLOPs. It fits in 2 GiB but forfeits the entire point of a small model.

So AETHER proposes **entropy plus a floor**, and explicitly labels it **uncalibrated**. A controller
built on an uncalibrated signal must be conservative: its thresholds must be set so that a
mis-calibrated confidence causes extra work rather than premature termination. The asymmetry is
deliberate — over-computing wastes seconds; under-computing produces a wrong answer presented
confidently.

### 5.3 The calibration AETHER actually needs

For the controller in §6, what matters is not absolute calibration but **monotonicity**: does a higher
entropy reading correlate with a higher chance of error? That is measurable with a small labelled set
and is the minimum bar before any threshold is chosen. **[OPEN]** — to be measured in Phase 6.

---

## 6. The proposed controller

An **external** controller. It is not part of the neural model, has no learned parameters, and can be
disabled entirely.

### 6.1 Structure

```
        request
           |
    [ classify ]  ── deterministic, no model call
           |
    budget = B_min                       (B_min = 1 generation)
           |
    [ generate ] ──> draft + confidence
           |
    [ test ] ── cheap deterministic checks (format, length, self-consistency of parse)
           |
     pass? ──yes──> return
           |
          no
           |
    budget < B_max ? ──no──> return best draft + explicit uncertainty note
           |
          yes
           |
    budget += Δ ; [ refine or re-generate ] ; loop
```

### 6.2 Parameters and their justification

| Parameter | Proposed value | Justification |
| --- | --- | --- |
| `B_min` | 1 generation | Simple requests must never pay for orchestration |
| `B_max` | 3 generations | Beyond this, cost grows faster than measured benefit in most orchestration literature; **unverified for AETHER** |
| `Δ` | 1 generation | Fixed step keeps accounting exact |
| Exit condition | deterministic test passes **or** `B_max` reached | Provable termination |
| Fallback | return `B_min` draft with an uncertainty note | **Deterministic** — identical input yields identical output |

### 6.3 Termination is a theorem, not a hope

`B_max` is finite, `Δ > 0`, so the loop terminates in at most `⌈(B_max − B_min)/Δ⌉ + 1` iterations. No
learned component participates in the termination decision, so a malformed model output cannot cause
an unbounded loop. This is the single most important property of the design.

### 6.4 The controller's own cost

| Component | Cost |
| --- | --- |
| Classification | **Zero model calls** — pattern matching over the request |
| Deterministic tests | Bytes scanned, negligible |
| Confidence read | Free — softmax already computed |
| Bookkeeping | A few dozen bytes |

**The controller costs no FLOPs.** It only *decides* whether to spend them. This is why it is proposed
over learned halting (§2.3), where the halting unit itself is a per-step matrix multiply.

### 6.5 Deterministic fallback

If every test fails and `B_max` is reached, AETHER returns the first draft and marks it low-confidence.
It does **not** return the last draft, because the last draft was produced under the most aggressive
refinement and is therefore the least predictable. Returning the `B_min` draft makes the degraded path
reproducible.

---

## 7. Why "more steps" is not monotonically better

Three mechanisms produce worse output from more computation:

1. **Over-thinking.** Repeated refinement can drift from a correct draft toward a plausible-but-wrong
   revision, because each pass conditions on the previous pass's errors.
2. **Confidence inflation.** A model asked to "try again" produces more fluent text, and fluent text is
   scored as more confident by the same signals used to decide whether to continue.
3. **Threshold hunting.** If a test is imperfect, iterating until it passes selects for outputs that
   fool the test — Goodhart's law applied inside a loop.

**[PROPOSED]** Because of these, AETHER's controller must treat additional passes as having
**unknown, possibly negative** value, and the evaluation in `EVALUATION_PLAN.md` §8 must measure the
capability curve **as a function of `B`**, not assume it rises.

---

## 8. What would change AETHER's mind

| Finding | Consequence |
| --- | --- |
| A trained AETHER model shows a clear BPC or accuracy gain from variable depth | Reopen learned halting |
| Entropy proves monotonic with error at 8 M parameters | Justify a confidence-driven controller |
| Wall-clock data shows repeated generation is a net win on a benchmark | Raise `B_max` |
| Wall-clock data shows repeated generation costs more than it earns | Set `B_max = B_min` = 1, making the controller a no-op |

The fourth outcome is entirely possible and would still be a result. A controller that was built,
measured, and found unnecessary has done its job.

---

## 9. Unresolved questions

1. Is entropy monotonic with error at AETHER's scale (§5.3)? **Blocks any threshold choice.** **[OPEN]**
2. Is `B_max = 3` defensible, or should it be 2 to bound the worst-case latency? **[OPEN]**
3. Does repeated generation measurably improve anything AETHER can evaluate? **Probably not — prior recorded.** **[OPEN]**
4. Should the controller be allowed to skip generation entirely for trivially cacheable requests? **[OPEN]**
5. How should the controller behave when the deterministic test is ambiguous rather than clearly
   failing? **Proposed: treat ambiguity as pass, prefer terminating.** **[OPEN]**
6. Does `binary32` nondeterminism (§2.3) make any threshold-based scheme unsafe in practice, or only
   in principle? **Unmeasured.** **[OPEN]**

---

## 10. Status summary

| Item | Status |
| --- | --- |
| ACT / PonderNet reviewed | **Established** — `[S29]`, `[S30]` |
| ACT's LM result (no large gain) | **Established** — the decisive negative evidence |
| Learned halting in the Core | **Rejected** for Phase 2, with reasons |
| MoE | **Rejected** on memory grounds, not compute |
| External controller design | **Proposed** — §6 |
| Controller cost | **Zero FLOPs by construction** (§6.4) |
| Termination guarantee | **Provable** (§6.3) |
| Confidence calibration | **Uncalibrated**; monotonicity unmeasured |
| Any implementation | **None.** No controller exists. |
