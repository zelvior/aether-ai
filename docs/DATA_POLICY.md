# AETHER — Data Policy

This policy governs any data used by the AETHER project: training corpora, evaluation sets,
tokenizer construction material, and any derived artefacts. It applies to data used for research,
even when that data is not redistributed.

It is a statement of project practice, **not legal advice**. Data protection obligations vary by
jurisdiction and by dataset; where they apply, they must be assessed rather than assumed.

---

## 0. Current state

**No datasets are used or distributed by this project at this time.** The project is at the
foundation stage; there is no training pipeline and no training data. This policy exists so that
requirements are fixed before data is ever introduced.

## 1. Core rules

These are not negotiable:

1. **No data without provenance.** If the origin of a dataset cannot be documented, it cannot be
   used.
2. **No data without a recorded license and permission basis.** "Available online" is not
   permission.
3. **No data with unclear training or redistribution terms.** Ambiguity is a reason to exclude, not
   a reason to proceed carefully and hope.
4. **Never describe a dataset as "legally cleared"** unless that claim has actually been verified by
   someone qualified, and the verification is recorded. Unverified datasets are recorded as
   *unverified*.
5. **Nothing enters this repository** unless its redistribution is permitted by its own terms.

## 2. Dataset manifests

Every dataset used — including temporary or experimental use — must have a manifest entry in the
repository, stored under a `data/` manifest path chosen when the training work begins. Manifests are
plain-text records (YAML or Markdown), not the data itself.

A manifest entry must record at minimum:

| Field | Requirement |
| --- | --- |
| Identifier | Stable name used in experiment configs |
| Source | Exact origin: URL, repository, publisher, or collection |
| Retrieval date | When the specific copy was obtained |
| Version or hash | Immutable identifier (commit, release tag, file hash) of the exact data |
| Composition | What it contains: language, domain, format, size, record count |
| License | Exact license or terms of use, with a link to the text |
| Permission basis | Why training on it is permitted; who granted it, if anyone |
| Redistribution | Whether redistributing it or derived weights is permitted, and under what terms |
| Personal data | Whether personal data is present, and the assessment behind that answer |
| Sensitive content | Known presence of sensitive categories, and treatment |
| Filtering | What was removed, and why |
| Deduplication | Method applied, and approximate effect |
| Preprocessing | Normalization, tokenization, redaction steps |
| Known issues | Quality problems, bias noted in documentation, contested status |
| Status | `candidate`, `approved`, `rejected`, `retired` — with the reason |

A dataset whose manifest is incomplete may not be promoted to `approved`.

## 3. Permissions and licensing

- **Training permission and redistribution permission are different things.** A dataset may be
  usable for training but not redistributable, or the reverse. Both must be recorded separately.
- **Derived weights.** Consider whether the dataset's terms constrain the release of weights trained
  on it. Record the conclusion and its basis, and see
  [`LICENSE_POLICY.md`](LICENSE_POLICY.md) §5.
- **Non-commercial and research-only licenses** are a reason to exclude a dataset from any use that
  could be characterized as anything other than non-commercial research. The project's default
  posture is to exclude them unless a specific decision is recorded.
- **Unlicensed data is excluded.** No license is not permission.
- **Licence changes** — if a dataset's terms change after use, record the change, assess the impact
  on already-trained artefacts, and decide explicitly whether to keep or retire it.

## 4. Personal and sensitive data

- Data must be assessed for personal data **before** it is used, and the assessment recorded — even
  when the conclusion is "none identified".
- Where personal data is present, prefer **removal** over obfuscation, and removal over aggregation.
- Special-category or sensitive data (health, biometric, financial, precise location, sexual
  orientation, political or religious belief, and comparable categories under applicable law) is
  excluded by default. Any exception requires a recorded maintainer decision with reasoning.
- **No secrets or credentials** may enter training data, manifests, or test fixtures. Scrape-adjacent
  corpora are to be scanned for keys, tokens, and addresses.
- Test fixtures and examples must use **synthetic** data, not samples of real people's data.
- Data of minors must not be used.

## 5. Opt-out and removal obligations

- Where a data source provides an opt-out, removal, or do-not-train mechanism, it must be respected.
- Removal requests concerning data used by this project must be honoured promptly, and the effect
  recorded: the manifest entry is updated, and the consequence for already-trained artefacts is
  assessed and documented.
- If a dataset publisher withdraws permission, the dataset is marked `retired`, its use stops, and
  the impact on existing artefacts is documented. Weights derived from it may need to be withdrawn
  or retrained; that decision is recorded rather than deferred.
- The maintainer is the current point of contact for such requests. See
  [`../SUPPORT.md`](../SUPPORT.md) for the public channels, and note that no dedicated address for
  data requests exists yet.

<!-- MAINTAINER ACTION REQUIRED: designate and publish a data-provenance and removal-request
     contact once this project uses any external dataset. -->

## 6. Filtering, deduplication, and preprocessing

These steps must be **documented and reproducible**, not applied ad hoc:

- **Filtering** — what was removed (categories, languages, sources, quality thresholds), with the
  rule or model used and the resulting counts.
- **Deduplication** — the method (exact, near-duplicate, hash-based), the granularity, and the
  approximate reduction. Duplicates distort training and inflate apparent quality.
- **Preprocessing** — normalization, encoding handling, truncation, and any redaction step.
- **Determinism** — the pipeline must be re-runnable to produce the same dataset version.
- **Dataset hashing** — the final dataset is identified by a hash or immutable version, and
  experiments reference that identifier.

Steps that were tried and produced worse results should be recorded too; see
[`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md).

## 7. Quality and contamination

- **Contamination.** Evaluation data must not appear in training data. Where a contamination check
  is possible, it is performed and recorded. Where it is not, that is stated as a limitation.
- **Splits** must be defined before training, and documented. No re-drawing splits after a result is
  known.
- **Quality assessment** is recorded: provenance signals, duplication, boilerplate, unusable language
  mix, and known issues in the publisher's own documentation.
- **Documentation claims by publishers are not verification.** If a dataset is described as
  "high-quality" or "clean" by its publisher, that is recorded as a claim, not a fact.

## 8. What this project will not do

- Use a dataset whose terms it cannot state.
- Describe a dataset as legally cleared or rights-free without verification.
- Redistribute restricted data inside this repository.
- Train on data it does not have permission to train on, on the grounds that the output is
  "transformed".
- Present unverified publisher claims as project findings.

## 9. Checklist before using any dataset

- [ ] Manifest entry created and complete
- [ ] Source, retrieval date, and immutable version recorded
- [ ] License text located and stored (link plus archived copy where possible)
- [ ] Training permission basis documented
- [ ] Redistribution permission basis documented, including for derived weights
- [ ] Personal and sensitive data assessment recorded
- [ ] Filtering, deduplication, and preprocessing documented and reproducible
- [ ] Dataset hash recorded and referenced by the experiment configuration
- [ ] Contamination check performed against evaluation data, or its absence stated
- [ ] Status set to `approved` by a maintainer
- [ ] If unverified: **labelled as unverified**, and not described as cleared
