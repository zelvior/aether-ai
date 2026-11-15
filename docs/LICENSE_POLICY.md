# AETHER — License Policy

This policy explains which license applies to what, how third-party material is handled, and what
must be checked before anything is redistributed. It is a statement of project practice, **not legal
advice**, and it is not a substitute for jurisdiction-specific review.

---

## 1. Scope of Apache-2.0 in this repository

Original material in this repository — source code, build scripts, documentation, and
specification text authored for AETHER — is licensed under the
[Apache License, Version 2.0](../LICENSE).

That covers, by default:

| Material | Default license |
| --- | --- |
| Original source code | Apache-2.0 |
| Build and CI configuration | Apache-2.0 |
| Documentation and specifications | Apache-2.0 |
| Issue templates, governance, and policy text | Apache-2.0 |

Exceptions must be stated explicitly in the file or directory. If a file carries its own license
header, that header governs.

## 2. Material that Apache-2.0 does *not* automatically cover

The repository license is a license to **this repository's content**. It is not a blanket license
to everything that might ever be associated with the project.

The following are **separate works** with possibly different terms, and must be licensed and
recorded explicitly before distribution:

| Material | Status in this repository |
| --- | --- |
| Model weights / checkpoints | **None distributed.** Terms undefined; see §5. |
| Training datasets | **None distributed.** See [`DATA_POLICY.md`](DATA_POLICY.md). |
| Tokenizer vocabulary assets | None yet. Will be treated as an explicit decision, not a default. |
| Evaluation datasets and benchmark suites | Third-party, with their own terms |
| Third-party source code and dependencies | Their own licenses; see §4 |
| Third-party documentation | Its own license; not covered by Apache-2.0 |
| Names, logos, and project marks | See §8 |

**Key rule:** a license on a repository's *code* does not automatically cover that repository's
*weights* or *datasets*. Many open machine-learning projects license code permissively while
applying different, or no, terms to weights and data. That distinction must be checked, not
assumed, for any upstream project this one draws on.

## 3. Contributor provenance

Every contribution must state its origin. Accepted forms are:

- Original work, submitted under Apache-2.0, consistent with Section 5 of the License.
- Third-party material whose license permits inclusion under Apache-2.0 terms, with source, version,
  and license recorded.
- Clearly licensed material that is *quoted* rather than incorporated, with attribution (for
  example a quoted passage in a research document).

Not accepted: code with unknown or unstated license, code copied without attribution, material whose
license is asserted only informally in prose, and material whose provenance the contributor cannot
establish. See [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## 4. Dependency license compatibility

AETHER uses **inbound = outbound Apache-2.0**. A dependency must be usable under terms compatible
with distributing AETHER under Apache-2.0.

### Generally acceptable

- Permissive licenses: Apache-2.0, MIT, BSD-2-Clause, BSD-3-Clause, ISC, Zlib, Unlicense, CC0.
- Public domain material, where provenance is documented.

### Requires care and explicit justification

- **LGPL** — acceptable only if the dependency is dynamically linked, replaceable, and does not
  impose obligations on AETHER's own code. Static linking of LGPL code requires a specific,
  reviewed decision.
- **MPL-2.0** — acceptable for separate, unmodified files, provided those files' terms are honoured.
  Modifications to MPL files stay under MPL.
- **CC-BY / CC-BY-SA** for documentation or data — documentation material may be included with
  attribution; **CC-BY-SA is viral for adaptations**, so material must not be adapted into
  Apache-2.0 documentation without a deliberate decision recorded in the pull request.
- **Dual-licensed** dependencies — pick a compatible license explicitly and record the choice.

### Not acceptable in distributed code

- **GPL** (any version) linked into or combined with AETHER code that is distributed.
- **AGPL**, for the same reasons plus network-use obligations.
- **SSPL**, **BUSL**, **Elastic License**, or other source-available licenses with field-of-use or
  time-based restrictions.
- **Non-commercial**, **research-only**, or otherwise restricted-use licenses.
- **No license at all.** Absence of a license is not permission.

### Attribution-based licenses and Apache-2.0

Apache-2.0 requires that recipients of a distributed work receive the license and the relevant
`NOTICE` content. This is why dependencies need recorded attribution: see §6.

## 5. Model weight redistribution

No model weights are distributed by this repository. If weights are released in the future:

- [ ] A license for the weights is chosen **before** release and stated explicitly, for each
      released model.
- [ ] The choice is recorded in a model card based on
      [`MODEL_CARD_TEMPLATE.md`](MODEL_CARD_TEMPLATE.md).
- [ ] The relationship between the weights license and Apache-2.0 is stated plainly: the repository
      license does not silently extend to weights, and the weights license does not silently extend
      to code.
- [ ] Training-data provenance is consistent with releasing the resulting weights. See
      [`DATA_POLICY.md`](DATA_POLICY.md).
- [ ] Any base model, checkpoint, or derivative relationship is disclosed, including that model's
      terms.
- [ ] A hash or checksum of each distributed artefact is published, with a documented way to verify
      it.

The project has **no position yet** on whether weights will be permissively or restrictively
licensed. That decision belongs to the maintainer and will be made in public, before any release.

**MAINTAINER ACTION REQUIRED:** record the intended weights license here once decided. Until then,
no weights may be released.

## 6. Third-party attribution requirements

When third-party material is added:

1. **Record it** in [`../NOTICE`](../NOTICE), with the component name, copyright holder, license, and
   a pointer to the full license text.
2. **Bundle the license text** where the license requires it.
3. **Preserve headers.** Do not strip copyright or license notices from third-party files.
4. **Mark modifications** clearly, consistent with Apache-2.0 §4(b).
5. **Keep the record current.** Removing third-party notices when a dependency is removed is fine;
   silently losing them is not.

A dependency without an attribution record is a review blocker, not a follow-up task.

## 7. Dataset provenance and permissions

Datasets are governed in detail by [`DATA_POLICY.md`](DATA_POLICY.md). The licensing summary is:

- Every dataset used must have a recorded license and documented permission basis for the intended
  use, including training.
- A dataset's *availability* is not the same as *permission to train on it and redistribute derived
  weights*.
- Datasets with unclear terms must not be used.
- Redistribution of a dataset inside this repository must be permitted by its own terms. In general,
  AETHER will **not** redistribute datasets; it will record provenance and pointers instead.

## 8. Names and marks

The Apache-2.0 trademark clause (§6) permits reasonable and customary use of the project name to
describe the origin of the work. It does **not** grant permission to use the AETHER name as a brand
for a derivative product.

- No trademark registration is claimed for "AETHER".
- No certification, endorsement, or "official" status is implied by anyone using or modifying this
  license or this codebase.
- Forks are welcome, and should not present themselves as the upstream project.

## 9. What the project does not claim

This policy is deliberately plain about limits:

- The project is **not** legally reviewed.
- The project is **not** certified for compliance with any standard or regulation.
- No patent position is asserted beyond the patent grant contained in Apache-2.0 §3.
- Policy documents describe intended practice and are **not legal advice**. Anyone with
  jurisdiction-specific obligations — especially redistributing derived weights or commercial
  use — should obtain their own advice.

## 10. Review checklist

Before merging a change that touches licensing:

- [ ] New files are original or have a recorded, compatible license.
- [ ] No dependencies were added without justification and a license check.
- [ ] `NOTICE` reflects any new third-party material.
- [ ] Bundled license texts are present where required.
- [ ] No code with unknown, missing, or restrictive licensing was included.
- [ ] No weights or datasets were added without the checks in §5 and §7.
- [ ] Documentation about licensing is accurate about what is and is not claimed.
