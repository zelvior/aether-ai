# AETHER

**An experimental, CPU-first AI model and inference ecosystem, built from scratch.**

AETHER is a research and development project exploring whether an AI model system can be
designed around efficient execution on ordinary CPUs — including legacy 32-bit x86 hardware —
rather than assuming a GPU or a large pretrained checkpoint is available.

AETHER is at an early, foundation stage. There is no model, runtime, tokenizer, or benchmark
result to report yet. This repository currently contains project structure, governance, and
policy documentation only.

---

## Table of contents

- [Project mission](#project-mission)
- [Core objectives](#core-objectives)
- [Design principles](#design-principles)
- [Target hardware and platforms](#target-hardware-and-platforms)
- [Development philosophy](#development-philosophy)
- [Planned components](#planned-components)
- [Project status](#project-status)
- [Design documents](#design-documents)
- [Planned development phases](#planned-development-phases)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Project mission

Build an original, efficient, CPU-first AI model ecosystem designed to support legacy 32-bit
x86 hardware alongside modern x86-64 systems.

The project exists to explore a question that mainstream model development largely treats as
answered: *how far can a carefully designed model and runtime get on constrained, widely
available hardware, without depending on proprietary weights or heavyweight infrastructure?*

## Core objectives

- **Build the model from scratch.** Architecture, tokenizer, training pipeline, and runtime are
  developed within this project rather than assembled around an existing pretrained checkpoint.
- **No mandatory pretrained weights.** A working system should be produced by this project's own
  training process. Pretrained checkpoints must never be a hard requirement to run or study it.
- **Efficient memory and compute utilization.** Memory footprint and instruction cost are design
  constraints, not afterthoughts.
- **Native 32-bit x86 compatibility as a first-class goal.** Not a port, not a fallback, not a
  "supported if it compiles" statement.
- **Portable, lightweight inference.** Minimal runtime surface, minimal dependencies, predictable
  behaviour across targets.
- **Privacy-conscious design.** Local execution and data minimization are preferred defaults.
- **Transparent research and reproducible experiments.** Claims should be checkable, and
  experiments should be repeatable by someone else.
- **Open-source development.** Development happens in public, under an OSI-approved license.
- **No unnecessary dependencies or duplicated components.** Every dependency and every module
  must justify its existence.

## Design principles

| Principle | What it means in practice |
| --- | --- |
| Measure, then claim | A property of the system is only described once it has been demonstrated and documented. |
| Constraint-driven design | 32-bit address space and modest memory are inputs to the design, not later optimizations. |
| One component, one purpose | No duplicate tokenizers, loaders, or math kernels with overlapping responsibilities. |
| Portability over cleverness | Straightforward, auditable code that builds on more targets beats target-specific tricks. |
| No hidden requirements | If something needs a dependency, a model file, or a network connection, that must be stated. |
| Reversible decisions | Early designs should be easy to discard when experiments contradict them. |

## Target hardware and platforms

AETHER's hardware goals are **design intentions that have not yet been validated**. Compatibility
is not established for any target listed here.

| Target class | Notes |
| --- | --- |
| 32-bit x86 (i386/i686-class) | The primary engineering constraint. Address-space and register limits drive model and runtime design. |
| 64-bit x86 (x86-64) | The expected development and reference platform. |
| Other architectures | Out of scope for now. May be revisited if the design proves portable in practice. |

Operating system and toolchain support will be specified only after real build and test
environments exist. No operating-system support claim is made at this stage.

## Development philosophy

1. **Specification before implementation.** The architecture and formats are described in writing
   before code depends on them.
2. **Prototype small, then scale.** A small, fully understood model is more useful than a large,
   unexplained one.
3. **Correctness before speed.** An optimization is adopted only after the baseline is understood
   and the result is reproducible.
4. **Everything is provisional.** Early design documents are working hypotheses, not commitments.
5. **Negative results are results.** Experiments that fail are documented so they are not repeated.

## Planned components

The following components are **planned**. None of them exist yet.

- **AETHER Architecture** — the model design itself: its layers, parameters, and design rationale,
  chosen to suit constrained CPU execution.
- **AETHER Tokenizer** — a tokenizer designed and implemented within the project, with a
  documented vocabulary and file format, rather than borrowed from another model.
- **AETHER Training** — the training pipeline: data handling, objective, checkpointing, and
  reproducible experiment configuration.
- **AETHER Runtime** — the inference engine that loads and executes AETHER models on supported
  hardware, with explicit attention to memory safety and bounded resource use.
- **AETHER Model Format** — a documented container and file format for weights, tokenizer assets,
  and metadata, designed for safe parsing and straightforward portability.
- **AETHER Evaluation** — the measurement methodology and tooling used to evaluate models on
  multiple task categories, including honest baseline comparisons.

Component names describe intent. Their scope may change as research progresses.

## Project status

**Early research / foundation stage.**

What exists today:

- Repository structure, licensing, contribution, governance, and policy documents.
- A tentative roadmap and research principles.
- **Phase 2 research and design specifications** (proposals, not results): a literature survey, an
  architecture specification, a memory budget, a numerical strategy, a model-format specification, a
  tokenizer specification, and an evaluation plan. See [Design documents](#design-documents).

What does not exist today:

- No model, no trained weights, no tokenizer, no runtime, no model format implementation.
- No training code and no datasets.
- No benchmarks, no performance numbers, and no compatibility results.
- **No part of the proposed design has been implemented or measured.** Every parameter count, memory
  figure, and compute count in the specifications is derived analytically from a proposal.

If a document in this repository ever appears to describe a completed capability, treat it as a
documentation bug and report it.

## Design documents

Phase 2 produced **twenty-seven design documents** (listed below, alongside the eight Phase 1
governance documents). They are **proposals**. They describe what AETHER intends to build and how it
intends to measure it; they are not descriptions of working software, and no figure in them has been
measured on AETHER hardware.

| Document | Contents |
| --- | --- |
| [`docs/RESEARCH_SURVEY.md`](docs/RESEARCH_SURVEY.md) | Literature review: architectures, CPU/memory constraints, numerics, tokenization, training feasibility |
| [`docs/ARCHITECTURE_SPEC.md`](docs/ARCHITECTURE_SPEC.md) | Proposed model: layers, dimensions, parameter accounting, compute accounting, alternatives |
| [`docs/MATHEMATICAL_FOUNDATIONS.md`](docs/MATHEMATICAL_FOUNDATIONS.md) | Forward and backward derivations, activation memory, BPC, initialisation |
| [`docs/OPTIMISATION_THEORY.md`](docs/OPTIMISATION_THEORY.md) | μP, learning-rate transfer, why the current transfer assumption is biased |
| [`docs/SCALING_LAW_ANALYSIS.md`](docs/SCALING_LAW_ANALYSIS.md) | What published fits predict at 8.4M parameters, and why to distrust it |
| [`docs/MEMORY_BUDGET.md`](docs/MEMORY_BUDGET.md) | Storage, runtime, peak inference, and training memory budgets against a 32-bit envelope |
| [`docs/NUMERICAL_STRATEGY.md`](docs/NUMERICAL_STRATEGY.md) | Numeric types, accumulation, overflow handling, determinism, x87 policy |
| [`docs/MODEL_FORMAT_SPEC.md`](docs/MODEL_FORMAT_SPEC.md) | Container format: byte layout, validation sequence, malformed-file handling |
| [`docs/TOKENIZER_SPEC.md`](docs/TOKENIZER_SPEC.md) | Byte-level BPE: vocabulary, specials, encoding/decoding, determinism |
| [`docs/MULTILINGUAL_RESEARCH.md`](docs/MULTILINGUAL_RESEARCH.md) | Per-script UTF-8 costs, merge-budget allocation, Roman Urdu's unsolved orthography |
| [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) | Metrics, baselines, 32-bit vs 64-bit protocol, forbidden comparisons |
| [`docs/TRAINING_FEASIBILITY.md`](docs/TRAINING_FEASIBILITY.md) | Why 32-bit training is out of scope, what training actually costs, and the pipeline test model |
| [`docs/INTELLIGENCE_DENSITY_RESEARCH.md`](docs/INTELLIGENCE_DENSITY_RESEARCH.md) | Why no single density metric is proposed, and the measurement matrix instead |
| [`docs/ADAPTIVE_COMPUTATION.md`](docs/ADAPTIVE_COMPUTATION.md) | Learned halting, MoE and early exit evaluated; an external controller proposed instead |
| [`docs/TRAINING_STRATEGY.md`](docs/TRAINING_STRATEGY.md) | Initialisation, objectives, data pipeline, checkpointing, reproducibility |
| [`docs/COGNITIVE_SYSTEM_SPEC.md`](docs/COGNITIVE_SYSTEM_SPEC.md) | Task classification, template planning, verification, termination |
| [`docs/MEMORY_SYSTEM_SPEC.md`](docs/MEMORY_SYSTEM_SPEC.md) | Persistent memory format, retrieval, conflict handling, deletion |
| [`docs/TOOLS_SYSTEM_SPEC.md`](docs/TOOLS_SYSTEM_SPEC.md) | Tool registration, default-deny permissions, sandboxing, threat model |
| [`docs/KNOWLEDGE_SYSTEM_SPEC.md`](docs/KNOWLEDGE_SYSTEM_SPEC.md) | BM25-first retrieval, ingestion, attribution |
| [`docs/RUNTIME_SPEC.md`](docs/RUNTIME_SPEC.md) | Loading, prefill/decode, kernels, determinism, resource limits |
| [`docs/ECOSYSTEM_ARCHITECTURE.md`](docs/ECOSYSTEM_ARCHITECTURE.md) | Why six components instead of one model — and when that argument fails |
| [`docs/CPU_32BIT_RESEARCH.md`](docs/CPU_32BIT_RESEARCH.md) | Address space, x87, SIMD availability, overflow discipline |
| [`docs/PLATFORM_COMPATIBILITY_PLAN.md`](docs/PLATFORM_COMPATIBILITY_PLAN.md) | The claim ladder: how a compatibility claim is earned, and why none exists yet |
| [`docs/EXPERIMENTAL_METHODOLOGY.md`](docs/EXPERIMENTAL_METHODOLOGY.md) | Admissibility, run manifests, ablations, statistical honesty |
| [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) | The costed programme that decides whether scale helps — about 5 days of compute |
| [`docs/RESEARCH_REFERENCES.md`](docs/RESEARCH_REFERENCES.md) | Annotated registry of every cited source, with limitations |
| [`docs/PHASE2_FINDINGS.md`](docs/PHASE2_FINDINGS.md) | What Phase 2 established, the six errors it corrected, and what it cannot know |

The proposal in one paragraph: an 8 425 728-parameter sliding-window decoder designed for CPU
execution, with a 1 840 256-parameter variant as the first model to be trained. Analytic peak inference
memory is about 100 MiB, well inside a conservative 2 GiB 32-bit address-space budget. **This is a
design statement, not a result.** Whether it can be built and whether it runs on 32-bit x86 are open
questions that Phase 4 onwards must answer.

## Planned development phases

The phases below are **planned and tentative**. Sequence and scope may change. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for detail and for the distinction between completed,
in-progress, and planned work.

| Phase | Focus | State |
| --- | --- | --- |
| 1 | Repository foundation | Completed |
| 2 | Research and architecture specification | In progress |
| 3 | Tokenizer development | Planned |
| 4 | Minimal neural network prototype | Planned |
| 5 | Training pipeline | Planned |
| 6 | Native inference engine | Planned |
| 7 | 32-bit x86 compatibility testing | Planned |
| 8 | Optimization and quantization | Planned |
| 9 | Evaluation and iteration | Planned |

## Contributing

Contributions are welcome, particularly in design review, documentation, testing strategy, and
portability research. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before opening a pull request.

Research directions should be raised through the research proposal issue template so they can be
discussed before implementation begins. See [`SUPPORT.md`](SUPPORT.md) for where questions belong.

## Security

Please do not report security issues in public issues. See [`SECURITY.md`](SECURITY.md) for the
disclosure process, and [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md) for the anticipated
threat model of the planned components.

## License

Original project code, documentation, and specification text are licensed under the
**Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

The Apache-2.0 license on this repository's code does **not** automatically cover model weights,
datasets, or third-party assets. Those are governed separately — see
[`docs/LICENSE_POLICY.md`](docs/LICENSE_POLICY.md). No model weights or datasets are distributed
by this repository at this time.

## Disclaimer

AETHER is an experimental project. **No capabilities, benchmarks, performance characteristics,
compatibility guarantees, or fitness for any purpose are established or claimed.**

Nothing in this repository constitutes legal advice. The policy documents here describe intended
project practice; they are not a substitute for jurisdiction-specific legal review. Specifically:

- There is no certification, patent, trademark, or legal review associated with this project.
- 32-bit x86 support is a stated design goal, not a demonstrated capability.
- Any future benchmark or compatibility number must be traceable to a documented, reproducible
  experiment, and must be read together with its stated conditions.

The software, when it exists, is provided on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
ANY KIND, as set out in the [Apache License 2.0](LICENSE).
