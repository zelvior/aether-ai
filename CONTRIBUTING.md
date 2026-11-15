# Contributing to AETHER

Thank you for considering a contribution. AETHER is an experimental, from-scratch research
project, so the most valuable contributions are often careful design review, measurement, and
documentation rather than large code drops.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Table of contents

- [Before you start](#before-you-start)
- [Contribution workflow](#contribution-workflow)
- [Pull request requirements](#pull-request-requirements)
- [Code quality expectations](#code-quality-expectations)
- [Testing expectations](#testing-expectations)
- [Documentation requirements](#documentation-requirements)
- [Attribution requirements](#attribution-requirements)
- [Third-party code and dependencies](#third-party-code-and-dependencies)
- [Licensing provenance](#licensing-provenance)
- [Where to ask questions](#where-to-ask-questions)

---

## Before you start

1. Read [`README.md`](README.md) and [`docs/PROJECT_VISION.md`](docs/PROJECT_VISION.md) to
   understand scope.
2. Check [`docs/ROADMAP.md`](docs/ROADMAP.md) — the project is at the foundation stage, so many
   implementation areas are not open for code yet.
3. For anything beyond a typo fix, **open an issue first**. Use the research proposal template for
   design or direction changes.
4. Wait for maintainer agreement on direction before investing in a large implementation.

Discussion before implementation is a requirement here, not a formality: this project has an
explicit goal of avoiding duplicated components and speculative code.

## Contribution workflow

1. **Find or open an issue.** Describe the problem, the proposed change, and what evidence
   supports it. Design-level changes need a research proposal.
2. **Get agreement on direction.** A maintainer will confirm scope, or explain why it is out of
   scope for now.
3. **Fork** the repository and create a topic branch from the current default branch. Do not work
   on `main` directly.
4. **Make a focused change.** One logical change per pull request. Unrelated cleanup belongs in a
   separate PR.
5. **Test what you changed**, and say in the PR exactly what you ran.
6. **Open a pull request** against the default branch and complete every section of the template.
7. **Respond to review.** Review comments are part of the process, and changes may be requested
   for reasons of scope, portability, or legal hygiene, not only correctness.

Commits should be readable: describe *what* changed and *why*. Squashing or rebasing to keep
history clean is welcome.

## Pull request requirements

A pull request is only reviewable when it contains all of the following. The
[pull request template](.github/PULL_REQUEST_TEMPLATE.md) repeats these as checkboxes.

- **Change summary** — what the change does, in one or two sentences.
- **Motivation** — the problem or research question it addresses, and a link to the agreed issue.
- **Testing performed** — exactly what was run, on what platform and toolchain, and what the
  result was. "Works for me" is not sufficient. If nothing was tested, say so explicitly.
- **Compatibility impact** — whether the change affects portability. Call out anything that is
  64-bit-specific, assumes a large address space, relies on a non-standard library, or would fail
  to compile on a 32-bit x86 target. If you cannot assess this, say so instead of guessing.
- **Licensing implications** — whether new files introduce third-party material, and under what
  license. See [Licensing provenance](#licensing-provenance).
- **Documentation updates** — which documents were updated, or why none were needed.

Additionally:

- No change may claim a capability, benchmark, or compatibility result that has not been
  demonstrated by a documented experiment.
- No change may add a dependency without justification (see below).
- No change may silently weaken a policy document in [`docs/`](docs/).

## Code quality expectations

These apply once implementation begins; they are recorded now so the standard is known up front.

- **Clarity over cleverness.** Code is read far more often than it is written, and must be
  reviewable by contributors who are not specialists in the specific area.
- **Portability by default.** Avoid undefined behaviour, implementation-defined behaviour,
  unchecked size assumptions, and platform-specific intrinsics unless they are isolated behind a
  documented abstraction with a portable fallback.
- **Be explicit about widths and sizes.** Do not assume `int` is 32 bits or that `size_t` is 64
  bits. Use fixed-width types where the representation matters, and check for overflow in size and
  offset arithmetic.
- **No silent failure.** Errors must be returned or reported, not ignored, especially in file
  parsing and allocation paths.
- **Bounded resource use.** No unbounded allocation, recursion, or buffering driven by external
  input.
- **Match the surrounding style.** Consistent formatting, naming, and file layout within a
  component. Repository-wide conventions are set in [`.editorconfig`](.editorconfig).
- **Keep it small.** New abstractions need a reason to exist. Prefer deleting a duplicate over
  adding a generic layer.

## Testing expectations

- New behaviour needs tests. A bug fix needs a regression test that fails before the fix.
- Tests must be **deterministic and offline**. No network access, no wall-clock dependence, no
  reliance on a specific machine's speed.
- State the platform and toolchain you tested on. If a change is platform-specific, say which
  platforms were actually exercised.
- **Do not claim 32-bit x86 support based on a 64-bit build.** Until a real 32-bit build and test
  environment exists in CI, 32-bit compatibility can only be asserted as *untested* or *validated
  locally by the contributor, with details*. Never as verified by the project.
- Performance changes must come with a reproducible measurement method and the raw numbers, not
  just a percentage. See [`docs/RESEARCH_PRINCIPLES.md`](docs/RESEARCH_PRINCIPLES.md).

## Documentation requirements

- Behaviour changes require corresponding documentation changes in the same pull request.
- Design decisions that are not obvious from the code belong in a document under [`docs/`](docs/)
  or in the pull request description, and should not be duplicated in both.
- Update [`docs/ROADMAP.md`](docs/ROADMAP.md) when a phase's state changes.
- Follow the existing Markdown conventions: one top-level heading, a table of contents for long
  documents, relative links for in-repository references, and no dead links.
- Documentation must be accurate about project state. It is better to write "not implemented" than
  to describe an intended design in the present tense.

## Attribution requirements

- Do not remove or alter existing copyright notices, license headers, or attribution statements.
- When you add material derived from another project, credit the upstream project, its authors, and
  its license in the same pull request.
- Significant contributions are recorded through the repository's version history and, where
  appropriate, the [`AUTHORS`](AUTHORS) file. Do not add yourself or anyone else to `AUTHORS`
  without maintainer agreement.
- Do not add names, affiliations, or contact details for other people without their consent.

## Third-party code and dependencies

AETHER aims to keep its dependency surface small. Accordingly:

- **Justify every new dependency** in the pull request: what it provides, why it cannot reasonably
  be implemented in-repository, its size and transitivity, and its maintenance status.
- **Check license compatibility.** Inbound material must be compatible with Apache-2.0 and must not
  impose terms on the project that its license cannot satisfy. See
  [`docs/LICENSE_POLICY.md`](docs/LICENSE_POLICY.md) for the rules, including the treatment of
  copyleft and source-available licenses.
- **Record attribution.** New third-party components require a matching entry in
  [`NOTICE`](NOTICE) and, where the license requires it, a bundled license text.
- **Vendored code is a last resort.** If code is vendored, keep it unmodified where possible, mark
  the modifications clearly, and record the exact upstream version and commit.
- **No dependency may be added solely for convenience** in a component whose purpose is to be
  dependency-free — in particular the runtime and model format parsers.
- **Do not add paid services, telemetry, or network calls** to build or test paths.

## Licensing provenance

This is a hard requirement, not a guideline.

**Do not submit code you cannot license.**

You must be able to state, for every file you contribute, that either:

- you wrote it and you are submitting it under the Apache License 2.0, consistent with
  [Section 5 of the License](LICENSE); or
- it comes from a source whose license permits inclusion under Apache-2.0 terms, and you have
  recorded the source, version, and license.

The following are **not acceptable**, even if the code "works":

- Code copied from another repository without its license and attribution.
- Code whose license is unknown, unstated, or described only in a README.
- Code generated by an AI tool or copied from a source whose licensing you cannot establish.
- Code taken from a project under an incompatible license, with or without modification.
- Model weights, tokenizer vocabularies, or datasets copied from another project without an
  explicit license that permits your intended use.

If you are unsure about the provenance of a piece of code, do not submit it. Ask first.

Maintainers will decline or remove contributions with unclear provenance. In practice this means a
pull request may be closed for licensing reasons even when its technical content is good.

## Where to ask questions

- Usage and general questions: [`SUPPORT.md`](SUPPORT.md).
- Design and research discussions: research proposal issue template.
- Security issues: [`SECURITY.md`](SECURITY.md) — **never** in a public issue.

---

Contributions are accepted under the terms of the [Apache License 2.0](LICENSE), and the project
does not currently require a separate contributor license agreement. If that changes, it will be
announced before it takes effect.
