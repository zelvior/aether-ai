# AETHER — Cognitive System Specification

Status: **Design proposal.** No component is implemented. Nothing here is measured, and no interface
described here exists as code.

Related: [`ADAPTIVE_COMPUTATION.md`](ADAPTIVE_COMPUTATION.md) (why the Core stays fixed-depth) ·
[`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md) · [`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) ·
[`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) · [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md)

---

## 1. Why orchestration exists at all

AETHER's Core is an 8.4 M-parameter language model. It cannot plan, it cannot call a tool, it cannot
remember last week's conversation, and it cannot verify its own arithmetic. Those are not bugs to be
fixed by a bigger Core — at AETHER's scale they are not reachable at all
([`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5.1).

Orchestration is the response: **put the capabilities the Core lacks into deterministic software
around it.** A task decomposer written in C is exact where a 8 M-parameter model would be noisy.

### 1.1 The warning this design must obey

`[S47]` argues that human-like intelligence requires structured cognitive models *combined with* neural
learning — and it is also the strongest available warning against the opposite error. A sophisticated
surrounding architecture is **not** a more capable neural model. `EVALUATION_PLAN.md` §11 makes this a
rule: no ecosystem-level improvement may be attributed to the Core, and every subsystem's contribution
must be ablated separately.

**AETHER's honest position:** the orchestration may make the *system* more useful while the *model*
remains equally limited. Both statements must be reported.

---

## 2. Component boundary

```
                    ┌─────────────────────────────┐
   user request ───▶│      ORCHESTRATOR           │
                    │  (deterministic, in C)      │
                    └──────┬──────────────────────┘
                           │
        ┌──────────┬───────┼────────┬──────────┐
        ▼          ▼       ▼        ▼          ▼
   ┌────────┐ ┌───────┐ ┌─────┐ ┌───────┐ ┌─────────┐
   │ MEMORY │ │TOOLS  │ │KNOW-│ │ CORE  │ │ADAPTIVE │
   │ SYSTEM │ │SYSTEM │ │LEDGE│ │ (NN)  │ │CONTROL  │
   └────────┘ └───────┘ └─────┘ └───────┘ └─────────┘
```

| Component | Nature | Deterministic | Parameters |
| --- | --- | --- | --- |
| Orchestrator | Software | **Yes** | 0 |
| Memory | Software + files | **Yes** | 0 |
| Tools | Software | **Yes** | 0 |
| Knowledge | Software + index | **Yes** | 0 |
| Core | Neural network | Yes (given fixed input) | 8,425,728 |
| Adaptive control | Software | **Yes** | 0 |

**Exactly one component has parameters.** Everything else is deterministic software, which is why the
system's behaviour is auditable in a way a monolithic model's is not.

---

## 3. Task classification

The orchestrator's first job is to decide how much machinery a request deserves. **This must not
require a model call**, or the cost of deciding exceeds the cost of answering.

### 3.1 The classification ladder

Cheapest tests first; the first match wins:

| Level | Test | Example | Cost |
| --- | --- | --- | --- |
| 0 | Exact match in cache | Repeated greeting | Hash lookup |
| 1 | Fixed-form command | `\help`, `\reset` | Prefix compare |
| 2 | Single-slot template | "define X", "translate ... to Urdu" | Token pattern |
| 3 | Retrieval-shaped | Contains a question about an indexed document | Keyword probe |
| 4 | Tool-shaped | Contains an arithmetic expression or date | Grammar match |
| 5 | General generation | Everything else | **Core call** |

**[PROPOSED]** Levels 0–4 are pattern matching over the raw request, requiring **zero FLOPs** from the
Core. Only level 5 and the generation step of levels 2–4 invoke the model.

### 3.2 What classification cannot do

A deterministic classifier cannot recognise a novel task. A request phrased unusually falls to level 5
— which is correct and safe. The failure mode is **cost**, not correctness: an easy request gets
treated as general. That asymmetry is deliberate and mirrors `ADAPTIVE_COMPUTATION.md` §5.2.

### 3.3 Why not classify with the Core

Using the model to decide whether to use the model doubles the model calls for every request. At
AETHER's inference cost ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §7.2: 18.94 MFLOP/token,
context-independent) that is not affordable for a request that turns out to be trivial.

---

## 4. Planning and decomposition

### 4.1 The hard constraint

At 8.4 M parameters, AETHER's Core **cannot plan**. `[S34]` shows chain-of-thought reasoning emerging
at 540 B parameters; the gap is roughly 10⁵×. Proposing a learned planner would be the single clearest
violation of the project's own principles.

### 4.2 What replaces it

| Approach | Determinism | Capability | Adopted? |
| --- | --- | --- | --- |
| Learned planner in the Core | Deterministic | **Not achievable at this scale** | No |
| Model-generated plan text, parsed and executed | Fragile — parse failure on malformed output | Low | **No** |
| Static plan templates selected by classification | **Total** | Narrow but reliable | **Yes** |
| Explicit user-specified pipeline | Total | Exact | Yes, where offered |

**[PROPOSED]** Decomposition is **template-based**. The orchestrator matches the request against a small
set of known multi-step shapes (e.g. *retrieve → summarise*, *parse expression → evaluate → format*)
and executes the corresponding fixed pipeline. Novel shapes are not decomposed; they are answered in
one generation and the answer is **not** presented as a reasoned plan.

### 4.3 Why not let the model emit a plan and parse it

This is the standard agent pattern and AETHER declines it, for three reasons:

1. **The parser is an attack surface.** Model output is untrusted input
   ([`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) §2). Parsing a plan means parsing arbitrary text
   into an executable structure.
2. **Failure is silent.** A malformed plan either fails to parse (visible) or parses into something
   unintended (invisible).
3. **It manufactures the impression of reasoning.** A fluent plan that is executed literally produces
   output that looks reasoned but is not verified at any step.

The third reason is the serious one. See `EVALUATION_PLAN.md` §11.

---

## 5. Execution state

### 5.1 What is tracked

| Field | Type | Purpose |
| --- | --- | --- |
| `turn_id` | monotonic counter | Audit, correlation |
| `level` | 0–5 | Which path was taken (§3) |
| `budget_used` / `budget_max` | generations | `ADAPTIVE_COMPUTATION.md` §6.2 |
| `stage` | enum | Where in the pipeline |
| `tools_invoked` | bounded list | Audit |
| `retrievals` | bounded list of doc ids | Attribution |
| `aborted` | flag + reason | Failure diagnosis |

### 5.2 Resource bounds on the state itself

The state must be **fixed-size and small**. A bounded list of 32 tool invocations and 32 retrieval ids
is a few KB; an unbounded list is a memory-exhaustion vector driven by model output.

**[PROPOSED]** Every field has a hard maximum. Exceeding it is a **terminated request with an error**,
not an unbounded growth.

---

## 6. Tool coordination

Detailed in [`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md). The orchestrator's responsibilities here:

| Responsibility | Rule |
| --- | --- |
| Decide *whether* a tool may be called | Classification level 4, or an explicit user request |
| Supply arguments | **From parsed request or user input — never from generated text alone** |
| Enforce permission | Per-tool allowlist, checked before execution |
| Enforce limits | Timeout, output-size cap, memory cap |
| Validate result | Type and range check before the result re-enters context |

**The orchestrator never executes a tool because the model suggested it.** The model may *request* a
tool; the orchestrator validates the request against the schema and the permission set and decides
independently. This is the single most important security property in the design and is expanded in
[`TOOLS_SYSTEM_SPEC.md`](TOOLS_SYSTEM_SPEC.md) §2.

---

## 7. Verification

### 7.1 What can be verified cheaply, and what cannot

| Output type | Verifiable? | Method |
| --- | --- | --- |
| Arithmetic | **Yes, exactly** | Recompute in integer/decimal — never trust the model |
| Citation to retrieved text | **Yes** | Substring check against the retrieved span |
| Format (JSON, date, number) | **Yes** | Grammar |
| Code | **No** — running it is a tool-execution risk | Not verified in Phase 2 |
| Factual claim | **No** | Requires a knowledge base AETHER does not have |
| Reasoning quality | **No** | No oracle exists |

**The asymmetry drives the design:** verify what is cheaply verifiable, and be explicit about the rest.
A system that claims to "verify" an output it cannot check is worse than one that admits the gap.

### 7.2 Arithmetic must never be done by the Core

An 8.4 M-parameter model will make arithmetic errors ([`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md)
§5). A decimal evaluator is exact, costs microseconds, and has no parameters. Routing arithmetic to a
tool is not a workaround — it is the correct architecture for this scale, and it is why
`EVALUATION_PLAN.md` §2 requires arithmetic tasks to be reported **with and without** tool access.

---

## 8. Failure recovery

| Failure | Detection | Response |
| --- | --- | --- |
| Core produces degenerate output | Repetition / length / control-character check | One retry at the same level, then return with an uncertainty note |
| Tool times out | Watchdog | Report timeout; **never** substitute a generated answer silently |
| Retrieval returns nothing | Empty result | Answer without retrieval, **stating** that no source was found |
| Output fails validation | Grammar check | One repair attempt, then fail cleanly |
| Budget exhausted | Counter | Return best draft + uncertainty note (`ADAPTIVE_COMPUTATION.md` §6.5) |

**[PROPOSED]** The invariant: **a degraded answer is always labelled.** The system may answer worse; it
may not answer worse while appearing confident.

---

## 9. Termination

The system terminates when any of these holds — all are decidable without model cooperation:

1. A deterministic test passes.
2. `budget_used == budget_max`.
3. A resource limit is hit (timeout, memory, output size).
4. The user aborts.

No path exists in which termination depends on the model choosing to stop. An EOS token ends a
*generation*, not a *turn*; the turn ends when the orchestrator's conditions are met.

---

## 10. Cost accounting

| Operation | Cost |
| --- | --- |
| Classification | ~0 (string ops) |
| Planning (template) | ~0 |
| Core generation | `T_out × 18.94 MFLOP` (Config M, context-independent) |
| Retrieval | Index lookup — no neural cost |
| Tool call | Tool-dependent |
| Verification | ~0 except tool-evaluated arithmetic |

**Every cost is attributable.** That is only possible because exactly one component has parameters, and
it is what makes `EVALUATION_PLAN.md` §11's separate-attribution requirement satisfiable.

---

## 11. What this system is not

- It is **not** an agent framework. There is no dynamic tool discovery at runtime, no self-directed
  goal decomposition, no learned policy.
- It is **not** a reasoning system. It routes, retrieves, computes and verifies; it does not reason.
- It does **not** make the Core smarter. It makes the *system* usable within the Core's limits.

---

## 12. Unresolved questions

1. How many plan templates are worth maintaining before maintenance cost exceeds benefit? **[OPEN]**
2. Should the model be permitted to *request* a tool at all, or should tool use be purely
   user/detector-driven? **Proposed: permit requests, require independent validation.** **[OPEN]**
3. What is the right output-size cap before truncation? **[OPEN]**
4. Does the level classifier handle Urdu/Hindi/Roman Urdu input at all without a model call? **Unverified.** **[OPEN]**
5. How is a "degenerate output" detected without false-positiving on legitimate repetition? **[OPEN]**
6. Should verification failures be shown to the user or only logged? **Proposed: shown, briefly.** **[OPEN]**

---

## 13. Status summary

| Item | Status |
| --- | --- |
| Classification ladder | **Proposed** — zero-FLOP levels 0–4 |
| Planning | **Template-based only**; learned planning rejected as unreachable at scale |
| Execution state | **Proposed**, fixed-size and bounded |
| Tool coordination | **Specified** — model may request, never authorize |
| Verification | **Specified** for arithmetic, citations, format; explicitly absent for facts and reasoning |
| Termination | **Decidable without model cooperation** |
| Implementation | **None.** No orchestrator exists. |
