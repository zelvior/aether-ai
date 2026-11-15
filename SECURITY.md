# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities in public issues, discussions, or pull requests.**

Public disclosure of an unpatched vulnerability puts users at risk. If you believe you have found a
security issue in this project, report it privately and give the maintainer a reasonable opportunity
to investigate and fix it before any public disclosure.

### How to report

Private vulnerability reporting is **not currently enabled** for this repository. To report an
issue, use one of the following, in order of preference:

1. **GitHub private vulnerability reporting**, once the maintainer enables it
   (*Settings → Code security and analysis → Private vulnerability reporting*). This is the
   intended long-term channel and avoids disclosing anything publicly.
2. **A private channel agreed with the maintainer in advance.** A dedicated security contact
   address has not yet been established; it will be published here once it exists.

<!-- MAINTAINER ACTION REQUIRED: enable GitHub private vulnerability reporting, or publish a
     dedicated security contact address, and replace this note with the confirmed channel.
     Do not add an address here until it is real and monitored. -->

There is currently **no general-purpose security email address** for this project. Do not assume
that any address found elsewhere on the internet reaches the maintainer.

### What to include

A useful report contains:

- A description of the issue and the component affected.
- The affected version, commit, or branch.
- Steps to reproduce, ideally a minimal proof of concept.
- The impact you believe it has, and the conditions required to trigger it.
- Any suggested mitigation.
- How you would like to be credited, or a request to remain anonymous.

Do not include real personal data, live credentials, or third-party confidential material in a
report. If a proof of concept requires data, use synthetic input.

### What to expect

This is a small, early-stage project maintained on a best-effort basis. There is no formal
response-time guarantee. In good faith, the maintainer will aim to:

1. Acknowledge the report.
2. Confirm or dispute the issue, and ask clarifying questions if needed.
3. Develop and test a fix privately.
4. Coordinate a disclosure date with you.
5. Credit you in the advisory or release notes, unless you prefer otherwise.

Please allow reasonable time for each step before disclosing publicly. If a report goes
unacknowledged for a long period, a reminder through a second private channel is reasonable before
any public disclosure.

## Supported versions

AETHER has **no released versions** at this stage. No version of any component is currently
supported, and no security fixes are being backported to anything.

| Version | Supported |
| --- | --- |
| *(none released)* | — |

Once releases exist, this table will be replaced with the actual supported-version policy,
including support windows and end-of-life rules. Until then, the only branch of interest is the
default branch, and it is under active, unreviewed development.

Security fixes, when they exist, will be applied to the default branch. The maintainer may also
issue advisories for publicly disclosed issues.

## Disclosure policy

- **Do not publicly disclose an unpatched vulnerability.** This includes issues, pull requests,
  social media, and conference talks.
- Fixes are developed on a private branch or a fork where possible, then merged with a description
  that does not disclose unpatched detail ahead of the coordinated date.
- Coordinated disclosure is preferred. The maintainer will work with the reporter on timing and on
  wording of any advisory.
- If the maintainer does not respond within a reasonable period despite repeated good-faith
  contact, the reporter may disclose, having documented the attempts to make contact.
- Reports that are already public will still be investigated, but the coordination options are
  limited.

## Scope

### In scope

Once the corresponding components exist, reports about the following are in scope:

- The model file parser and any deserialization path (malformed or hostile model files).
- The runtime and inference engine, particularly memory safety in native code.
- Build and packaging scripts, where a hostile input could influence the build output.
- The tokenizer and text preprocessing paths, including resource exhaustion.
- The training pipeline, where data handling could lead to code execution or data exposure.
- Published artifacts (archives, checksums) whose integrity could be subverted.
- Repository configuration that could allow unintended code execution, such as workflow
  permission mistakes.

### Out of scope

- The absence of a capability. AETHER has no security-hardening claims and no model to attack.
- Vulnerabilities in third-party dependencies with no exploitable path through this project.
  Report those upstream as well; the project may still need to pin, upgrade, or document them.
- Model output that is incorrect, unhelpful, or biased, unless it results from a concrete
  implementation flaw.
- Reports generated by automated scanners with no demonstrated impact.
- Social engineering, physical access, and denial-of-service against hosted infrastructure the
  project does not operate.

### Current state

There is no runtime, parser, or model to assess today. The anticipated security concerns for the
planned components are documented in [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md), which is
the useful starting point for anyone reviewing this area.

## Security review expectations

- Security-relevant changes (parsing, memory management, file I/O, dependency additions,
  serialization formats, workflow permissions) require explicit review with security in mind, not
  only functional review.
- Any parser or deserializer is expected to be written defensively from the start: length checks,
  allocation bounds, and rejection of malformed input as a normal, tested code path.
- Reviewers should assume model files and datasets are untrusted input. See
  [`docs/DATA_POLICY.md`](docs/DATA_POLICY.md) and
  [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md).
- Builds aim to be reproducible; deviations are to be documented rather than ignored.
- No workflow or script may use untrusted input in a way that grants it privileged execution
  (for example, interpolating issue titles directly into a shell command).
- Dependencies are reviewed for provenance and license at the point they are introduced. See
  [`docs/LICENSE_POLICY.md`](docs/LICENSE_POLICY.md).

## Safe harbour

The maintainer will not pursue legal action against researchers who:

- act in good faith and in accordance with this policy;
- avoid privacy violations, data destruction, and service disruption;
- test only against their own installations and data, not against third parties;
- report privately and give reasonable time to fix before disclosure.

This safe-harbour statement is a statement of intent by an individual maintainer. It is not a legal
agreement and does not override any applicable law.
