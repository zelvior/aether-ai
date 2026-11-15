# AETHER — Project Brief for ChatGPT

Paste this entire document as your first message to give ChatGPT complete context on the project.
It is self-contained: it assumes no prior knowledge of AETHER.

**Last updated:** 2026-11-15 · **Repository state:** `main` @ `5392b9a` · **Phase:** 1 (foundation),
nearly complete, Phase 2 not started.

---

## 1. What I am building

**AETHER** is an experimental, from-scratch AI model and inference ecosystem with a **CPU-first**
design philosophy. Its defining constraint is that **legacy 32-bit x86 hardware is a first-class
target**, not an afterthought, alongside modern x86-64 systems.

The central research question:

> How far can a carefully designed model and runtime get on constrained, widely available
> CPU hardware — without depending on proprietary pretrained weights or heavyweight GPU
> infrastructure?

AETHER is **not** a product, not a wrapper around an existing inference engine, and not a commercial
endeavour. It is a research project developed in public.

| Fact | Value |
| --- | --- |
| Project name | AETHER |
| Repository | `aether-ai` |
| GitHub | `github.com/zelvior/aether-ai` |
| Owner | Zelvior (Zelvior Labs), `@zelvior`, Pakistan |
| License | Apache License 2.0 |
| Visibility | Public |
| Default branch | `main` |
| Status | Early research / foundation stage |
| Approach | Built from scratch; no mandatory pretrained weights |

---

## 2. Core principles

These are the project's non-negotiables. Any suggestion that violates one should be flagged.

1. **Built from scratch.** Architecture, tokenizer, training pipeline, and runtime are developed
   within the project — not assembled around someone else's checkpoint.
2. **No mandatory pretrained weights.** A working system must come from the project's own training
   process. A pretrained checkpoint can never be a hard requirement.
3. **Efficient memory and compute.** Footprint and instruction cost are design constraints, not
   later optimizations.
4. **Native 32-bit x86 compatibility as a first-class goal.** Not a port, not a fallback.
5. **Portable, lightweight inference.** Minimal runtime surface, minimal dependencies.
6. **Privacy-conscious design.** Local execution by default; no telemetry, no required network calls.
7. **Transparent, reproducible research.** Experiments must be repeatable by someone else.
8. **Open-source development.** Everything in public, under Apache-2.0.
9. **No unnecessary dependencies or duplicated components.** Every dependency and module must
   justify its existence.

### Design principles

| Principle | Meaning |
| --- | --- |
| Measure, then claim | A property is only described once demonstrated and documented. |
| Constraint-driven design | 32-bit address space and modest memory are *inputs*, not optimizations. |
| One component, one purpose | No duplicate tokenizers, loaders, or math kernels. |
| Portability over cleverness | Auditable portable code beats target-specific tricks. |
| No hidden requirements | Dependencies, model files, and network needs must be stated. |
| Reversible decisions | Early designs should be easy to discard when experiments contradict them. |

---

## 3. Planned components

All six are **planned and none exist yet**. Names describe intent; scope may change.

| Component | Purpose |
| --- | --- |
| **AETHER Architecture** | The model design — layers, parameters, rationale, sized for constrained CPU execution. |
| **AETHER Tokenizer** | Tokenizer implemented in-project, with a documented vocabulary and file format. |
| **AETHER Training** | Training pipeline: data handling, objective, checkpointing, reproducible config. |
| **AETHER Runtime** | Inference engine: loads and executes models, memory-safe, bounded resource use. |
| **AETHER Model Format** | Documented container for weights, tokenizer assets, metadata; safe parsing. |
| **AETHER Evaluation** | Measurement methodology and tooling; multi-category, honest baselines. |

---

## 4. Roadmap — 9 tentative phases

Sequence and scope may change. **There are no delivery dates.**

| # | Phase | State |
| --- | --- | --- |
| 1 | Repository foundation | **In progress** (11 of 12 items done) |
| 2 | Research and architecture specification | Planned |
| 3 | Tokenizer development | Planned |
| 4 | Minimal neural network prototype | Planned |
| 5 | Training pipeline | Planned |
| 6 | Native inference engine | Planned |
| 7 | 32-bit x86 compatibility testing | Planned |
| 8 | Optimization and quantization | Planned |
| 9 | Evaluation and iteration | Planned |

**Phase 1 — remaining work:** the only unchecked item is *"Maintainer decisions resolved"* (see §9).

**Phase 2 — next up, not started.** Deliverables:
- Survey of constrained-resource inference techniques, with citations
- Architecture specification: layers, dimensions, parameter budget, rationale
- Memory budget: target footprint under a 32-bit address space, with headroom
- Numeric strategy: data types, accumulation, overflow handling
- Model format specification: container, versioning, integrity checks, safe-parsing rules
- Tokenizer design specification: vocabulary strategy and file format
- A defined baseline, and what "better" will mean

**Explicitly out of scope for now:** GPU/CUDA/ROCm backends, distributed training, non-x86
architectures, hosted services or APIs, model sizes exceeding the memory budget, and any model
release before Phase 9 produces evaluated results.

---

## 5. Current repository state

`main` is at commit `5392b9a`. **27 files, ~3,800 lines.** Everything below exists and is merged.

```
aether-ai/
├── README.md                    190 lines   mission, objectives, status, phases
├── LICENSE                      201 lines   Apache-2.0, word-for-word official text
├── NOTICE                        44 lines   scope + third-party notice policy
├── CONTRIBUTING.md              190 lines   workflow, PR rules, provenance requirements
├── CODE_OF_CONDUCT.md           149 lines   Contributor Covenant 2.1
├── SECURITY.md                  145 lines   private disclosure, scope, review gates
├── SUPPORT.md                    73 lines   where to ask what
├── CITATION.cff                  41 lines   CFF 1.2.0, schema-validated
├── AUTHORS                       36 lines   maintainer only
├── .editorconfig / .gitattributes / .gitignore
├── .github/
│   ├── FUNDING.yml                          all values commented out
│   ├── PULL_REQUEST_TEMPLATE.md  88 lines
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml       121 lines
│   │   ├── feature_request.yml  104 lines
│   │   └── research_proposal.yml 134 lines
│   ├── workflows/repository-checks.yml 64
│   └── scripts/check_repository.py    421 lines
└── docs/
    ├── PROJECT_VISION.md        116 lines
    ├── ROADMAP.md               231 lines
    ├── GOVERNANCE.md            144 lines
    ├── LICENSE_POLICY.md        182 lines
    ├── DATA_POLICY.md           152 lines
    ├── MODEL_CARD_TEMPLATE.md   236 lines
    ├── SECURITY_MODEL.md        184 lines
    └── RESEARCH_PRINCIPLES.md   151 lines
```

### What the documents cover

- **PROJECT_VISION** — the question, why 32-bit x86, failable success criteria, non-goals.
- **GOVERNANCE** — single maintainer, decision types, 7-day comment period for policy changes,
  reviews, bus-factor mitigations.
- **LICENSE_POLICY** — what Apache-2.0 covers (original code, docs, CI) vs. what it does **not**
  (weights, datasets, tokenizer assets, third-party assets). Dependency license compatibility
  rules. Explicit statement that a code license does not imply a weights license.
- **DATA_POLICY** — dataset manifest schema (16 required fields), permission vs. redistribution
  distinction, personal-data assessment, opt-out/removal obligations, filtering and dedup
  documentation, contamination checks. Key rule: never call a dataset "legally cleared" without
  verification.
- **SECURITY_MODEL** — threat model for planned components: malicious training data, unsafe
  serialization (pickle banned), model-file parsing (validate before allocate, overflow-safe
  arithmetic), supply-chain risk, memory safety in native code, reproducible builds.
- **MODEL_CARD_TEMPLATE** — 16-section reusable template: identity, architecture, memory accounting,
  data, training procedure, intended use, limitations, evaluation, hardware compatibility,
  quantization, license, risks.
- **RESEARCH_PRINCIPLES** — reproducibility, baselines, measurable claims, honest reporting,
  ablations, multi-category evaluation, and an explicit list of forbidden misleading comparisons.

### Automation

`.github/scripts/check_repository.py` — **stdlib-only** Python, no dependencies. Runs on every push
and PR. Checks:
1. All 26 required files exist and are non-empty
2. No model weights, datasets, or secret files committed
3. YAML parses (PyYAML required in CI, not skippable silently)
4. Issue-form structure is valid (types, ids, labels, dropdown options)
5. `CITATION.cff` has required CFF keys, correct version, no invented DOIs
6. Every relative Markdown link and in-document anchor resolves
7. No CRLF, files end with newline
8. Reports any open maintainer placeholders

Also runs `citation-file-format/cffconvert-github-action@2.0.0` for independent CFF validation.
**The workflow deliberately does not build or test anything** — there is no code to build, and it
must not imply 32-bit compatibility testing exists.

---

## 6. Hard rules for this project

**Do not:**
- Invent benchmarks, performance numbers, or capability claims
- Claim 32-bit x86 compatibility before an actual 32-bit build has run
- Add pretrained model weights or datasets
- Add unnecessary dependencies
- Fabricate contributors, contact details, DOIs, ORCIDs, or third-party attribution
- Present generic policy language as legal advice
- Claim the project is certified, patented, trademarked, or legally reviewed

**Do:**
- Mark unverified things as unverified
- Use explicit placeholders where a maintainer decision is required
- Distinguish completed work from planned work — planned work is never written in the present tense
- Cite sources for borrowed numbers and label them cross-paper if they are

**Every claim in this project must be traceable to a reproducible experiment.**

---

## 7. Legal and licensing position

- **Apache-2.0** covers original code, documentation, specs, and CI config.
- **No weights, datasets, or tokenizer assets are distributed.** Their terms are deliberately
  undefined until a maintainer decision is recorded.
- **Contributors must satisfy provenance rules.** No code with unclear licensing; code from
  incompatible licenses is rejected; AI-generated code with unestablishable provenance is rejected.
- **Contributor Covenant 2.1** is used verbatim, licensed CC BY-SA 4.0, with attribution retained.
- The project requires **no CLA and no DCO** currently.

---

## 8. Target hardware

| Target | Status |
| --- | --- |
| 32-bit x86 (i386/i686) | The primary **design constraint**. Address-space limits drive model and runtime design. |
| 64-bit x86 (x86-64) | Expected development and reference platform. |
| Other architectures | Out of scope for now. |

**No compatibility claim exists for any target.** Operating-system and toolchain support will be
specified only after real build and test environments exist.

---

## 9. Open decisions — 6 placeholders, all marked `MAINTAINER ACTION REQUIRED`

These are unresolved in the repo. Do not treat any as decided.

| Decision | Location | Blocks |
| --- | --- | --- |
| Private conduct reporting contact | `CODE_OF_CONDUCT.md` | CoC enforcement |
| Security disclosure channel | `SECURITY.md` | Private vuln reports (GitHub private reporting is currently **disabled**) |
| Funding account | `.github/FUNDING.yml` | Sponsor button |
| Model weight licensing terms | `docs/LICENSE_POLICY.md` | Any future weight release |
| Data provenance / removal-request contact | `docs/DATA_POLICY.md` | Training on external data |
| Release metadata (version, date, DOI) | `CITATION.cff` | Formal citation |

---

## 10. How to work with me on this

**Where things are:** every policy, plan, and decision is documented in the repository. If a
question is answerable from those documents, the answer should match them — flag contradictions
rather than inventing a third version.

**Tone:** direct and technical. State limitations plainly. If something is unknown or unverified,
say so instead of estimating around it.

**When suggesting work:**
1. Say which roadmap phase it belongs to, or that it is out of scope.
2. Distinguish "this exists" from "this is planned".
3. Do not propose adding dependencies without justifying them.
4. For anything spanning more than one component, propose a research proposal first — that is the
   project's actual process.
5. Assume CPU-only hardware. Do not assume GPU access.

**What I want from you:** honest technical pushback is more useful than agreement. If a design idea
conflicts with the project's principles, or a claim cannot be supported by evidence the project
could actually produce, say so directly.

---

## 11. The immediate next step

**Phase 2 — Research and architecture specification.** Nothing has been written yet. No architecture
has been chosen, no parameter budget set, no numeric strategy decided.

This is deliberately the first real engineering work: the design must be specified in writing before
any code depends on it. Any proposal here should be a reviewable document, not an implementation.
