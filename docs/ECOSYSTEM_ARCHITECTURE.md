# AETHER — Ecosystem Architecture Rationale

Status: **Argument and analysis, not a result.** This document justifies the six-component design
against its alternatives. It contains no measurement, and the justification is explicitly contingent on
one empirical fact that AETHER does not yet have.

Related: [`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) · [`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md)
· [`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) · [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md)
· [`RUNTIME_SPEC.md`](RUNTIME_SPEC.md) · [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md)
· [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md)

---

## 1. The claim that needs defending

AETHER proposes six cooperating components: **Core** (the neural model) and five deterministic
subsystems — Cognitive, Memory, Tools, Knowledge, Runtime.

**Nothing in the Phase 2 documentation up to this point argues that this is the right decomposition.**
The individual specs describe *how* each subsystem would work. None of them answers:

> Why not one bigger model? Why not a monolith? Why six components rather than, say, three or twelve?

That is the weakest link in the project's reasoning, and this document is the attempt to close it —
including honestly reporting where the argument fails.

---

## 2. The four candidate architectures

| # | Architecture | Description |
| --- | --- | --- |
| **A1** | Monolithic model | One network does everything; no external subsystems |
| **A2** | Core + retrieval | A model plus a document index; the minimal modern pattern |
| **A3** | Six components | AETHER's proposal |
| **A4** | Agent framework | A model driving an open-ended tool ecosystem with learned planning |

### 2.1 Evaluation criteria

| Criterion | Why it matters here |
| --- | --- |
| **Parameter efficiency** | The binding constraint ([`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §1) |
| **Memory ceiling** | 512 MiB working target ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2) |
| **Capability reachable** | What the system can actually do |
| **Auditability** | Can a user see why it did something? |
| **Attack surface** | [`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) §2 |
| **Implementation cost** | Effort to build and maintain |
| **Determinism** | [`RUNTIME_SPEC.md`](RUNTIME_SPEC.md) §9 |

---

## 3. The decisive argument: arithmetic, not preference

### 3.1 What A1 would require

To match A3's *functional* reach with a single model, the model would need, in its weights:

| Capability | Where A3 puts it | Approximate parameter cost if internalised |
| --- | --- | --- |
| World knowledge | Knowledge index | `V × d` per fact-cluster — see below |
| Working memory across sessions | Memory store | Requires long context or recurrence |
| Exact arithmetic | Tool | **Not achievable** at any size |
| Planning | Template engine | Not achievable at 8 M |

**The third row is the one that settles the argument.** `COGNITIVE_SYSTEM_SPEC.md` §7.2 shows that
exact decimal arithmetic is *categorically* not a capability a `binary32` neural network acquires by
scaling — it is a discrete, unbounded-precision task. A transformer can approximate digit-wise addition
on bounded inputs; it cannot do arbitrary-precision decimal arithmetic reliably at any practical size.

So A1 is not merely expensive. **It is impossible for at least one of AETHER's required functions.**
Any architecture that claims exact arithmetic must have an external evaluator.

### 3.2 What world knowledge would cost inside the model

`[S37]` (RAG) motivates non-parametric knowledge; the arithmetic makes it concrete.

AETHER's embedding table is `V × d`. In Config M, `d = 256`. To store a *useful* body of world
knowledge in parameters, the model needs capacity proportional to the knowledge, and scaling laws
`[S9]` relate capacity to `P`. GPT-3's 175 B parameters were described as insufficient for reliable
factual recall `[S45]`-era work; AETHER has 8.4 M — **a factor of 20,000 fewer.**

| Approach | Parameters dedicated to knowledge | Update cost |
| --- | --- | --- |
| Parametric (Config M) | ≤ 8.4 M total, including everything else | Full retrain |
| Parametric (GPT-3 scale) | 175 B | Full retrain |
| **Non-parametric (A3)** | **0** | Re-index one document |

**AETHER cannot win the parametric knowledge race at any point in its realistic future.** Acknowledging
that is not a limitation of ambition; it is the reason the architecture looks the way it does.

### 3.3 The memory accounting of the full system

Never previously computed in this documentation. Peak RSS with all subsystems resident:

| Component | Resident | Source |
| --- | --- | --- |
| Core (weights + activations + KV + runtime) | 99.55 MiB | [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §5 |
| Memory index | 1.00 MiB | [`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md) §9 |
| Knowledge index (mapped) | 128.00 MiB | [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) §5.3 |
| **System total** | **≈ 228.55 MiB** | |

That is **11.2 % of the 2 GiB envelope** and **44.6 % of the 512 MiB working target**.

**This is the first time the whole system has been budgeted together**, and the result is reassuring but
not comfortable: the knowledge index is now the *largest single memory consumer*, more than twice the
Core's weights. If the index quota grows, it becomes the binding constraint on a 32-bit target, not the
model.

**[OPEN]** Whether a 128 MiB index is appropriate on a 256 MiB-RAM machine
([`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §8). The arithmetic says it is not, and the quota may
need to be profile-dependent.

---

## 4. A2 versus A3: where the argument is weakest

A2 (core + retrieval) is the minimal modern pattern and it captures the two largest wins: non-parametric
knowledge (§3.2) and the ability to run a small model at all.

**So why not stop at A2?**

| A3 subsystem | What it buys | Available in A2? |
| --- | --- | --- |
| Cognitive | Exact arithmetic, verification, deterministic termination | **No** |
| Memory | Cross-session state | **No** |
| Tools | Computation, dates, files | **No** |
| Knowledge | ✓ | ✓ |

**Three of the four subsystems A2 omits are justified by the same argument as §3.1:** they offload
something a small `binary32` network cannot do exactly.

The honest counter-argument: **A2 is far cheaper to build**, and A3's extra subsystems are three
additional attack surfaces, three additional failure modes, and three additional specs to maintain.

**[PROPOSED]** A3 is justified *if and only if* the Core is confirmed weak. If E1
([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) §3) shows a power-law regime with Config M reaching useful
capability, **A2 becomes the better engineering choice** and A3 is over-engineering.

This is stated as a genuine conditional, not a rhetorical hedge. The architecture's justification
depends on an experiment that has not been run.

---

## 5. A4 versus A3: why not an agent framework

| Property | A4 (agent framework) | A3 (AETHER) |
| --- | --- | --- |
| Tool selection | Model-driven, learned | Classification + templates |
| Termination | Model decides | **Provable** ([`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) §9) |
| Authorization | Often model-mediated | **Orchestrator only** |
| Attack surface | Open-ended | Closed permission set |
| Dependency weight | Large | Minimal |
| Capability ceiling | Higher | Lower |

**A4 is genuinely more capable.** It is rejected for three specific reasons, in order of weight:

1. **`[S31]`-class learned routing does not work at 8 M parameters.** The classification is a
   deterministic string match precisely because the model cannot be trusted to route
   ([`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) §3.3).
2. **Model-driven authorization violates the central security rule**
   ([`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) §1).
3. **Termination becomes undecidable** without an external budget enforcer.

Reason 1 is the one that is *specific to AETHER's scale*. At 70 B parameters, A4 would be the right
choice. At 8 M it is not.

---

## 6. Why six, and not three or twelve

The decomposition is not arbitrary; each boundary sits where a **different invariant** applies:

| Boundary | Invariant on one side | On the other |
| --- | --- | --- |
| Core ↔ everything | Has parameters; not deterministic across builds | Deterministic, zero parameters |
| Memory ↔ Knowledge | Per-user, mutable, deletable | Shared, immutable, re-ingestable |
| Tools ↔ Cognitive | Untrusted code, sandboxed | Trusted orchestrator logic |
| Runtime ↔ all | Numeric, error-code-returning | Text/structured, error-tolerant |

**A component boundary is justified exactly when it separates two different trust levels or lifetimes.**
Anything else is cosmetic layering, which is why A3 has six components and not twelve: there are four
genuine boundaries, plus the Core and the Runtime itself.

### 6.1 Where this test fails

The Cognitive and Knowledge subsystems share a trust level (both deterministic, both trusted) and differ
only in data source. A three-component design collapsing them would be defensible.

**[OPEN]** — whether to merge Cognitive and Knowledge is a maintainability question this analysis
cannot settle.

---

## 7. What would falsify the six-component design

| Finding | Consequence |
| --- | --- |
| E1 shows power-law regime with M reaching useful capability | **A2 becomes preferable**; collapse to core + retrieval |
| The orchestration's measured contribution is negligible (ablation) | Deleting the subsystem is correct |
| Tool use is never invoked in real sessions | The whole Tools subsystem is unjustified |
| Memory retrieval is never used across sessions | Memory subsystem unjustified |
| Memory index and knowledge index together exceed the target | **Forced merge or quota reduction** |

**These are registered as falsification conditions, not as caveats.** If the first occurs, AETHER should
be redesigned around A2 and this document should record that it was wrong.

---

## 8. The uncomfortable summary

| Question | Honest answer |
| --- | --- |
| Is A3 better than A1? | **Yes, decisively** — A1 cannot do exact arithmetic at any size (§3.1) |
| Is A3 better than A2? | **Unknown** — depends on the Core's capability, which is unmeasured (§4) |
| Is A3 better than A4? | **Yes at 8 M parameters**; no at frontier scale (§5) |
| Is six the right number? | **Probably** — four boundaries are genuine; one is soft (§6.1) |
| Is A3 what a well-resourced team would build? | **No** — they would build A2 and a bigger model |

The last row is the one worth sitting with. **AETHER's six-component design is a rational response to a
specific constraint: an 8 M-parameter model cannot do much, so the system must supply what the model
cannot.** If the constraint were lifted, the design would be wrong — and saying so is what makes the
justification credible.

---

## 8A. How the subsystem claim would be tested

`EVALUATION_PLAN.md` §7 forbids attributing system-level gains to the Core. That rule is only meaningful
if the subsystem contributions can actually be separated — and §4's argument is *contingent* on the
Core being weak. Neither is testable without an ablation design.

### 8A.1 The three optional subsystems

The Core and Runtime are always present; they are not ablatable. The three subsystems with a genuine
on/off choice are **Memory**, **Tools** and **Knowledge**.

### 8A.2 Full factorial versus one-at-a-time

| Design | Conditions | Detects interactions? |
| --- | --- | --- |
| One-at-a-time (all-on, minus each) | 4 | **No** |
| Full factorial `2³` | **8** | Yes |

| # | Memory | Tools | Knowledge |
| --- | --- | --- | --- |
| 1 | on | on | on |
| 2 | off | on | on |
| 3 | on | off | on |
| 4 | on | on | off |
| 5 | off | off | on |
| 6 | off | on | off |
| 7 | on | off | off |
| 8 | off | off | off |

**[PROPOSED]** The full factorial, for one reason: **the interactions are the interesting part.**

Concretely, Knowledge and Tools are expected to be **substitutes** for arithmetic-and-fact questions —
a calculator and a document index both answer "what is 17 × 23" differently but both answer it. A
one-at-a-time design would show each helping, and would miss that together they help **less than the sum
of their parts**. That interaction is exactly the kind of finding worth having.

| Effect | Formula | Interpretation |
| --- | --- | --- |
| Main effect `eff(S)` | `mean(Y \| S on) − mean(Y \| S off)` | The subsystem's average contribution |
| Two-way `eff(A×B)` | `eff(A\|B on) − eff(A\|B off)` | Whether they substitute or reinforce |
| Three-way | remainder | Usually noise at this scale |

### 8A.3 Cost

Eight conditions × one evaluation suite each. Because subsystems are deterministic software, no
retraining is needed — **the model is fixed across all eight conditions**, and the ablation is a
configuration sweep, not a training programme.

This is a real advantage of the decomposition: a monolithic model cannot be partially ablated at all.

### 8A.4 The falsification this enables

`§7` registers "orchestration contribution is negligible" as a falsification condition. §8A is how it
would be detected:

| Observation | Action |
| --- | --- |
| `eff(S) ≈ 0` and no interaction | **Delete the subsystem.** Maintaining it is unjustified |
| `eff(S) < 0` | Investigate — a subsystem making things worse is a defect |
| Large interaction | Redesign the boundary (§6) |

**AETHER should be prepared to delete a component.** A six-component design that keeps all six
components without evidence is not architecture, it is accretion.

## 9. Unresolved questions

1. Does the Core's capability justify A3 over A2 (§4)? **Depends on E1.** **[OPEN]**
2. Is the Cognitive/Knowledge boundary worth maintaining (§6.1)? **[OPEN]**
3. Should the knowledge index quota be profile-dependent rather than fixed at 128 MiB (§3.3)? **[OPEN]**
4. Can orchestration contribution be ablated as cleanly as
   [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §7 requires, given subsystems interact? **[OPEN]**
5. At what parameter count would A4 become defensible? **Unquantified.** **[OPEN]**

---

## 10. Status summary

| Item | Status |
| --- | --- |
| A1 rejected | **Decisively** — exact arithmetic is impossible in a `binary32` network at any size |
| Parametric knowledge rejected | **Decisively** — 20,000× parameter deficit |
| A2 vs A3 | **Contingent on E1** — not resolved, and not resolvable without it |
| A4 rejected at this scale | **Yes**, with the scale-dependence stated |
| Six-component count | **Argued** from four genuine trust/lifetime boundaries |
| Full-system memory (first time computed) | **228.55 MiB** — knowledge index now dominates |
| Any measurement | **None.** |
