# AETHER — Project Vision

Status: **Living document.** This describes intent, not delivered capability.

---

## The question

Most contemporary AI model development assumes abundant memory, wide vector units, and a GPU on
the path to running anything useful. AETHER starts from the opposite end: **what can be built by
treating a modest CPU as the primary target?**

Specifically, the project explores whether a model and runtime designed *around* the limits of
32-bit x86 — a 32-bit address space, limited registers, no assumption of SIMD width beyond what the
target guarantees — can still be a useful and honest piece of software.

AETHER does not claim to have answered this. It claims that the question is worth engineering
against, and that the answer should be measured rather than assumed.

## Why 32-bit x86

Restrictions are useful design constraints. A model system that fits and runs in a constrained
environment tends to be:

- **understood** — fewer moving parts, less implicit state;
- **portable** — nothing is allowed to depend on the assumption that memory is effectively vast;
- **inspectable** — arithmetic is explicit, so results can be reasoned about and reproduced;
- **accessible** — it runs on hardware people already own, including hardware that is otherwise
  written off.

32-bit x86 is also a field where a lot of deployed and discarded hardware still exists. Software
that treats it as an afterthought tends to break there. Treating it as a first-class target is a
statement about engineering priorities, not about sentimentality.

## What AETHER is

- An **original model**: architecture, tokenizer, training procedure, and runtime developed within
  the project rather than assembled around someone else's checkpoint.
- **CPU-first**: the execution target shapes the design, from parameter layout to arithmetic.
- **From scratch by default**: no mandatory pretrained weights, no required proprietary services.
- **Open**: everything, including the experiments that failed, developed in public.
- **Conservative about claims**: numbers only appear after they can be reproduced.

## What AETHER is not

- **Not a product.** There is no roadmap commitment, no support contract, and no release cadence.
- **Not a wrapper.** It is not a thin interface over an existing inference engine.
- **Not a claim of parity.** No comparison with any other model, library, or system is asserted or
  implied. Any future comparison must be measured, like-for-like, and documented.
- **Not finished.** At the time of writing, no model or runtime exists.

## Objectives

| Objective | How we would know we met it |
| --- | --- |
| Build the model from scratch | Tokenizer, architecture, and training code are all developed in-repository, with no pretrained checkpoint needed to run the result |
| No mandatory pretrained weights | A model can be produced and run purely from this project's own training process |
| Efficient memory and compute | Memory use and instruction cost are measured on stated hardware, and stay within stated budgets |
| Native 32-bit x86 compatibility | A 32-bit build is produced and executed in a documented test environment |
| Portable, lightweight inference | The runtime builds on supported targets with a minimal, recorded dependency set |
| Privacy-conscious design | Local execution is the default path; no required network calls or telemetry |
| Transparent, reproducible research | An independent person can repeat a reported experiment from the repository alone |
| Open-source development | Development happens in public under Apache-2.0 |

Each item in the right-hand column is a **test we have not yet run**. That is deliberate: an
objective without a way to falsify it is a slogan.

## Non-goals

- Chasing state-of-the-art benchmark scores on hardware the project does not target.
- Supporting architectures or operating systems that have not been deliberately prioritized.
- Maximizing parameter count for its own sake.
- Feature parity with large general-purpose ML frameworks.
- Providing any guarantee of model output quality, safety of generated text, or fitness for a
  particular use.

## Intended users

- **Researchers and engineers** interested in constrained-resource inference and from-scratch model
  design.
- **Retrocomputing and low-resource practitioners** who want to see modern techniques applied
  honestly to modest hardware.
- **Students and reviewers** who want a small, legible codebase to study end to end.
- **Contributors** who care about correctness over demo polish.

AETHER is not intended, at this stage, for production deployment of any kind.

## Success criteria for the foundation stage

The foundation stage is complete when the following are true:

1. Licensing, contribution, governance, and data policy documents exist and are internally
   consistent.
2. Repository checks run automatically and pass.
3. The architecture and model format have written specifications that can be reviewed.
4. The roadmap distinguishes clearly between planned, in-progress, and completed work.

None of these require a model to exist. That is the point of separating foundation work from
research work.

## Risks and how the project treats them

| Risk | Mitigation |
| --- | --- |
| Scope creep into a general ML framework | Non-goals are stated explicitly; new components must justify their existence |
| Unverifiable or inflated claims | Research principles require measurement, baselines, and reproducible reporting |
| 32-bit support becoming a slogan | Compatibility is only claimed after a real build and test; CI says nothing until then |
| Legal and licensing ambiguity in data and weights | Separate license and data policies, with provenance requirements |
| Memory-safety defects in native code | Security model defines parser and allocation expectations up front |
| Abandonment | Documents are written so the project state is understandable without prior context |

## What "success" looks like

Not a leaderboard position. Success is: a small, comprehensible model system that someone can read,
build, retrain, and reason about on ordinary hardware — with every number in its documentation
traceable to an experiment that can be repeated.
