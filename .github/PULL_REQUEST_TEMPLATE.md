<!--
  Thanks for contributing to AETHER. Please complete every section.
  A pull request with an empty section will be asked to complete it before review.
  For design-level changes, link the issue or research proposal where the direction
  was agreed. See CONTRIBUTING.md for the full requirements.
-->

## Change summary

<!-- What does this pull request do? One or two sentences. -->

## Motivation

<!--
  Why is this change needed? What problem or research question does it address?
  Link the agreed issue or research proposal, e.g. "Closes #12".
-->

## Testing performed

<!--
  State exactly what you ran, and on what. "Not tested" is an acceptable answer
  if it is true; an unverifiable claim is not.
-->

| Item | Detail |
| --- | --- |
| Commands run | <!-- e.g. `make test`, `ctest -R parser` --> |
| Platform / architecture | <!-- e.g. Linux x86-64; say if a 32-bit build was attempted --> |
| Toolchain and version | <!-- e.g. gcc 13.2.0, clang 17 --> |
| Result | <!-- pass/fail, and a one-line summary of output --> |
| New tests added | <!-- yes/no, and what they cover --> |

## Compatibility impact

<!--
  AETHER treats 32-bit x86 as a first-class target. Please assess this explicitly.
  Do not claim 32-bit support unless you actually built and ran on a 32-bit target.
-->

- [ ] No portability impact (documentation, policy, or tooling only)
- [ ] Portable change; builds and passes on both 32-bit and 64-bit targets I tested
- [ ] Portable change, but only verified on a 64-bit target (32-bit remains untested)
- [ ] Introduces a 32-bit-specific or 64-bit-specific code path (explain below)
- [ ] Not applicable

<!-- Details: size or offset assumptions, address-space needs, intrinsics, new
     platform dependencies, or why a 32-bit build was not possible here. -->

## Licensing implications

<!--
  See docs/LICENSE_POLICY.md and the "Licensing provenance" section of CONTRIBUTING.md.
-->

- [ ] I wrote this code and submit it under the Apache License 2.0
- [ ] This change includes third-party material; source, version, and license are recorded below
- [ ] This change includes no new dependencies and no third-party material
- [ ] This change adds or changes a dependency (justification below)
- [ ] This change includes model weights, tokenizer assets, or data (**generally not accepted**;
      see docs/DATA_POLICY.md before opening)

<!-- Provenance details, NOTICE updates, or dependency justification. -->

## Documentation updates

<!-- Which documents were updated, or why none were needed. -->

- [ ] Updated affected documents under `docs/`
- [ ] Updated `README.md` / `CONTRIBUTING.md` where relevant
- [ ] Updated `docs/ROADMAP.md` phase state (if applicable)
- [ ] No documentation change needed (explain why)

## Claim hygiene

<!-- This project does not publish unverified claims. -->

- [ ] This change does not claim any capability, benchmark, compatibility result, or performance
      figure that has not been demonstrated by a documented, reproducible experiment
- [ ] Any measurement included states its method, hardware, and conditions
- [ ] No fabricated names, contact details, contributors, or third-party attributions were added

## Checklist

- [ ] I read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`
- [ ] The change is focused; unrelated changes are in separate pull requests
- [ ] I reviewed my own diff for accidental inclusions (debug code, secrets, large binaries)
- [ ] If this is a security-relevant change, I followed `SECURITY.md` for reporting and review
