# AETHER — Governance

This document describes how decisions are made in the AETHER project, who makes them, and what
contributors can expect. It describes the project **as currently constituted**, which is small. It
does not describe an intended future structure as though that structure already exists.

---

## Current structure

AETHER currently has **one maintainer**:

- **Zelvior** ([@zelvior](https://github.com/zelvior)) — repository owner, maintainer, and current
  decision-maker.

There is no foundation, no committee, no steering group, no voting body, and no sponsored
governance. No additional maintainers, reviewers, or team members should be assumed to exist. The
[`AUTHORS`](../AUTHORS) file is the canonical list and is kept accurate.

## Maintainer responsibilities

The maintainer is accountable for:

| Area | Responsibility |
| --- | --- |
| Direction | Setting and documenting project scope, priorities, and non-goals |
| Architecture | Approving or rejecting design proposals; keeping specifications current |
| Review | Reviewing pull requests for correctness, portability, licensing, and scope |
| Licensing | Maintaining license compliance, `NOTICE` accuracy, and provenance records |
| Security | Handling private vulnerability reports and coordinating fixes and disclosure |
| Conduct | Enforcing the [Code of Conduct](../CODE_OF_CONDUCT.md) |
| Releases | Deciding when, whether, and how anything is released |
| Infrastructure | Repository settings, CI configuration, and access control |
| Documentation | Keeping the state of the project honestly described |

Being the only decision-maker is a practical arrangement for a small project, not a statement about
good governance at scale. It is also a concentration of risk: see
[bus factor and continuity](#bus-factor-and-continuity).

## Decision-making

### Principle

Decisions are made in public wherever possible, with the reasoning written down. "Because the
maintainer said so" is a valid tie-break, but the reasoning behind it should still be recorded.

### How decisions are made by type

| Decision type | Process |
| --- | --- |
| Typographical and documentation fixes | No prior approval needed; reviewed in the pull request |
| Bug fixes within existing documented behaviour | Pull request, reviewed against tests |
| New features within an agreed phase | Issue first, then pull request after maintainer agreement on scope |
| Architecture or research direction | **Research proposal issue**, public discussion, then a written decision record |
| Licensing, governance, or policy changes | Public proposal with a comment period (see below) |
| Breaking format or API changes | Proposal plus a documented migration path, before merge |
| Security fixes | Handled privately; summarized publicly after coordinated disclosure |

### Policy change comment period

Changes to `LICENSE`, `NOTICE`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, this document, or anything in
`docs/` that affects contributors' rights or obligations are proposed publicly and left open for
comment for at least **seven calendar days** before merge, unless the change is urgent for legal or
security reasons. Urgent changes are still announced and explained after the fact.

### Disagreement

If you disagree with a decision:

1. Say so in the relevant issue or pull request, with reasoning.
2. The maintainer will restate or revise the decision and record it.
3. If unresolved, the maintainer's decision stands, and the disagreement stays visible in the issue
   history rather than being deleted.

Persistent disagreement on fundamentals is a legitimate reason to fork. AETHER is Apache-2.0
specifically so that this is possible.

## Reviews

- **All changes go through pull requests.** The maintainer does not push directly to the default
  branch for substantive changes, and contributors should not expect direct push access.
- **Review covers more than correctness.** Scope, portability (including 32-bit implications),
  licensing provenance, test quality, and documentation are all review criteria. A correct change
  can be declined for being out of scope or for unclear provenance.
- **Self-review is a fallback, not a policy.** Since there is one maintainer, a change may be merged
  after self-review when no other reviewer is available. Such changes are labelled so the absence of
  independent review is visible.
- **Review turnaround is best-effort.** No response-time guarantee is offered. See
  [`../SUPPORT.md`](../SUPPORT.md).
- **Reviews are technical, not personal.** See the [Code of Conduct](../CODE_OF_CONDUCT.md).

## Contributions

Contributions are accepted under the [Apache License 2.0](../LICENSE). The project does not
currently require a contributor license agreement or a developer certificate of origin; provenance
requirements are described in [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

Submitting a pull request does not obligate the maintainer to merge it. A contribution may be
declined, asked to change, or closed for scope, quality, licensing, or timing reasons.

Contributors are credited in commit history, and in [`../AUTHORS`](../AUTHORS) where they agree.

## Releases

There have been **no releases**. When releases begin:

- They will be tagged in this repository with a version and a changelog entry describing actual
  changes.
- A release will state exactly what it contains, including whether any model weights or data are
  included and under what terms. See [`LICENSE_POLICY.md`](LICENSE_POLICY.md).
- No release will be published claiming capabilities that are not demonstrated in that release.
- Archive DOIs, if any, will be minted only when a release exists. None are claimed now.

Unreleased code on the default branch is under development and carries no stability guarantee.

## Project direction

Direction is set by the maintainer, informed by:

- [`PROJECT_VISION.md`](PROJECT_VISION.md) — the standing intent;
- [`ROADMAP.md`](ROADMAP.md) — the tentative sequence;
- [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) — the standard evidence must meet;
- research proposals and public discussion.

Direction changes are recorded in the roadmap and, for significant changes, in the pull request or
issue that approved them. Changes are not made silently.

## Bus factor and continuity

One maintainer is a single point of failure. Honest mitigations currently in place:

- **Everything is public** — there are no private design documents.
- **Documents describe state, not just intent**, so a newcomer can determine what exists.
- **Apache-2.0** guarantees the right to fork and continue the work.
- **Placeholders are explicit** — the repository does not pretend to have bodies or channels it
  does not have.

If the project grows, additional maintainers will be added with a documented process, and this
document will be updated to reflect the actual structure rather than an aspirational one.

## Amendments

This document can be amended by the maintainer following the comment period above. Amendments are
made by pull request and remain in version history.
