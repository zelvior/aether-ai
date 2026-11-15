# AETHER — Roadmap

Status: **Tentative.** This roadmap describes intended direction, not commitments. Sequence,
scope, and timing may change as research progresses. There are no delivery dates.

---

## How to read this document

Every item is labelled with one of three states:

| State | Meaning |
| --- | --- |
| **Completed** | Done, merged, and verifiable in this repository right now. |
| **In progress** | Actively being worked on. Not finished, and may be abandoned. |
| **Planned** | Intended, not started. May never start. |

Nothing is **Completed** unless it exists in this repository and can be checked. Planned work is
never described in the present tense. If you find a document that violates this, it is a bug.

**No phase below has produced a working model, runtime, or benchmark result.**

---

## Phase overview

| # | Phase | State | Depends on |
| --- | --- | --- | --- |
| 1 | Repository foundation | **In progress** | — |
| 2 | Research and architecture specification | Planned | 1 |
| 3 | Tokenizer development | Planned | 2 |
| 4 | Minimal neural network prototype | Planned | 2, 3 |
| 5 | Training pipeline | Planned | 4 |
| 6 | Native inference engine | Planned | 4 |
| 7 | 32-bit x86 compatibility testing | Planned | 6 |
| 8 | Optimization and quantization | Planned | 6, 7 |
| 9 | Evaluation and iteration | Planned | 5, 6 |

---

## Phase 1 — Repository foundation

**State: In progress**

Establish the non-technical groundwork so that research starts on a clean base.

- [x] Apache-2.0 license text in place
- [x] README describing mission, scope, and current status
- [x] NOTICE, AUTHORS, and licensing policy
- [x] Contribution guidelines and pull request requirements
- [x] Code of Conduct (Contributor Covenant 2.1) with maintainer placeholder for contact
- [x] Security policy and anticipated security model
- [x] Data policy and model card template
- [x] Governance and maintainer responsibilities
- [x] Research principles
- [x] Issue templates, pull request template, and funding configuration
- [x] Minimal repository checks workflow
- [ ] Maintainer decisions resolved (see [open decisions](#open-maintainer-decisions))

**Exit criteria:** checks pass in CI, documentation is internally consistent, and no placeholder
that blocks real use remains.

---

## Phase 2 — Research and architecture specification

**State: Planned**

Write down the model design before implementing it.

- [ ] Survey of constrained-resource inference techniques, with citations
- [ ] Architecture specification: layers, dimensions, parameter budget, rationale
- [ ] Memory budget: target footprint under a 32-bit address space, with headroom
- [ ] Numeric strategy: data types, accumulation behaviour, overflow handling
- [ ] Model format specification: container, versioning, integrity checks, safe parsing rules
- [ ] Tokenizer design specification: vocabulary strategy and file format
- [ ] Defined baseline for comparison, and what "better" will mean

**Exit criteria:** specifications are reviewable and contain no fabricated numbers. Any design
assumption that has not been tested is marked as an assumption.

**Note:** specifications are documents. They may be wrong, and are expected to change once
prototypes exist.

---

## Phase 3 — Tokenizer development

**State: Planned**

- [ ] Tokenizer implementation matching the Phase 2 specification
- [ ] Deterministic, documented vocabulary construction from training data
- [ ] Round-trip and edge-case tests (empty input, invalid UTF-8, very long input)
- [ ] Resource-limit behaviour defined and tested
- [ ] Tokenizer asset licensing and provenance recorded

**Exit criteria:** implementation is testable, dependency-light, and portable to 32-bit targets.

---

## Phase 4 — Minimal neural network prototype

**State: Planned**

The smallest model that is genuinely trainable and understandable.

- [ ] Minimal model implementation in portable code
- [ ] Forward pass verified against a hand-checked reference
- [ ] Parameter count and memory footprint measured
- [ ] Training on a small, documented corpus to demonstrate the pipeline works
- [ ] Prototype limitations documented

**Exit criteria:** a model can be trained and its outputs reproduced by another person.

---

## Phase 5 — Training pipeline

**State: Planned**

- [ ] Reproducible experiment configuration (seeds, data version, hyperparameters)
- [ ] Checkpointing and resume
- [ ] Data pipeline conforming to [`DATA_POLICY.md`](DATA_POLICY.md)
- [ ] Dataset manifests with provenance and license records
- [ ] Run logs sufficient to reconstruct a result
- [ ] Cost and resource reporting for each run

**Exit criteria:** a third party can repeat a documented run and obtain comparable results, within
stated tolerance.

---

## Phase 6 — Native inference engine

**State: Planned**

- [ ] Runtime implementation per the Phase 2 format specification
- [ ] Safe parser for model files, with malformed-input tests
- [ ] Explicit memory budgeting and failure behaviour on exhaustion
- [ ] Deterministic output for a fixed input and model
- [ ] Portable build; no unguarded 64-bit assumptions
- [ ] Reference outputs published as checksums for cross-platform comparison

**Exit criteria:** the engine runs a model on the development platform with documented behaviour.

---

## Phase 7 — 32-bit x86 compatibility testing

**State: Planned**

This phase cannot begin until a real 32-bit build and execution environment exists. Until then,
**no 32-bit compatibility claim is made anywhere in this repository.**

- [ ] Documented 32-bit build environment (toolchain, flags, target)
- [ ] Automated build on a 32-bit target
- [ ] Automated execution of tests on a real 32-bit environment
- [ ] Output equivalence checks against the 64-bit reference
- [ ] Memory ceiling validation under a constrained address space
- [ ] Known limitations and unsupported configurations documented

**Exit criteria:** CI produces and runs a 32-bit build, and equivalence results are published with
their conditions. Automated CI for this phase is added only once the environment exists — not
before.

---

## Phase 8 — Optimization and quantization

**State: Planned**

- [ ] Profiling on stated hardware, with methodology
- [ ] Quantization approach with numerical error measured, not estimated
- [ ] Trade-off tables: footprint, speed, and quality, measured on the same hardware
- [ ] Optimization results reported against a recorded baseline
- [ ] All optimizations behind documented, reversible switches where practical

**Exit criteria:** every reported change is reproducible from a documented command.

---

## Phase 9 — Evaluation and iteration

**State: Planned**

- [ ] Evaluation harness covering multiple task categories
- [ ] Clear separation of training, validation, and evaluation data
- [ ] Baselines: random, trivial, and any relevant reference system
- [ ] Uncertainty reporting: multiple seeds, variance, and known confounds
- [ ] Published results with full conditions and raw data
- [ ] Model cards for each evaluated model, using
      [`MODEL_CARD_TEMPLATE.md`](MODEL_CARD_TEMPLATE.md)
- [ ] Iteration based on findings, including documenting dead ends

**Exit criteria:** results are honest about what they do and do not show. See
[`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md).

---

## Explicitly out of scope for now

These are recorded so that they are not silently assumed:

- GPU acceleration, CUDA, ROCm, or any accelerator backend.
- Distributed or multi-machine training.
- Non-x86 architectures.
- A hosted service, API, or web interface.
- Model sizes that cannot fit the documented memory budget.
- Any published model release before Phase 9 produces evaluated, documented results.

Ideas in this list can be revisited, but doing so is a decision that requires a research proposal
and maintainer agreement.

## Open maintainer decisions

These are unresolved and are marked as placeholders elsewhere in the repository:

| Decision | Where | Blocks |
| --- | --- | --- |
| Private conduct reporting contact | `CODE_OF_CONDUCT.md` | Enforcement of the Code of Conduct |
| Security disclosure channel | `SECURITY.md` | Accepting private vulnerability reports |
| Funding configuration | `.github/FUNDING.yml` | Sponsor button |
| Model weight licensing terms | `docs/LICENSE_POLICY.md` | Any future weight release |
| Dataset provenance process owner | `docs/DATA_POLICY.md` | Any future training run on external data |

## How this roadmap changes

- Changes to phase scope or ordering require maintainer agreement and, for research direction, a
  research proposal issue.
- Items move to **Completed** only when the work is merged and verifiable here.
- This document is reviewed at the end of each phase.
