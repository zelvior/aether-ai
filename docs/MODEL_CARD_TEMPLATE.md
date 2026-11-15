# Model Card — [MODEL NAME]

> **Template.** Copy this file when documenting an actual model. Replace every bracketed field.
> Do not delete sections; write "not applicable" or "unknown" with a reason instead.
>
> **Rules for filling this in:**
> - A number you cannot reproduce does not go in this card.
> - "Unknown" is an acceptable and useful answer. An invented value is not.
> - This card describes the model as measured on stated hardware, not as intended.
> - If the model is not released, say so plainly in [Status](#1-model-identity).

---

## 1. Model identity

| Field | Value |
| --- | --- |
| Model name | [e.g. AETHER-mini-0.1] |
| Version | [version identifier] |
| Date | [YYYY-MM-DD of this card] |
| Status | [released / internal experiment / not released] |
| Maintainer | [name and contact channel] |
| Repository commit | [git commit hash of the code that produced this model] |
| Card revision | [revision of this document] |

## 2. Summary

[Two to four sentences: what this model is, what it was built to investigate, and what it is not.
No marketing language, no unsupported adjectives.]

## 3. Architecture

| Field | Value |
| --- | --- |
| Family | [e.g. transformer variant, or the AETHER architecture name] |
| Parameters | [total count, and trainable count if different] |
| Layers | [count and type] |
| Hidden dimension | [size] |
| Attention or mixers | [mechanism, heads, context handling] |
| Activation | [function] |
| Normalization | [method and placement] |
| Positional encoding | [method] |
| Context length | [tokens, training vs inference maximum] |
| Vocabulary size | [size, and tokenizer identity] |
| Embedding tying | [yes/no] |
| Specification reference | [link to the design document in this repository] |

Deviations from the referenced specification, if any: [list, or "none"]

## 4. Parameter and memory accounting

| Item | Value |
| --- | --- |
| Parameter count (exact) | [number] |
| Bytes per parameter (storage) | [e.g. 4 fp32, 2 fp16, 1 int8] |
| Weight footprint | [MiB, measured, not estimated] |
| Peak runtime memory | [MiB, measured under a stated input length] |
| Measured on | [hardware, OS, build flags] |
| Measurement method | [tool or procedure; link to script if in-repo] |
| 32-bit address-space headroom | [estimate of remaining space, or "not measured"] |

Do not estimate these. If unmeasured, write "not measured".

## 5. Training data

| Field | Value |
| --- | --- |
| Datasets used | [names, linked to manifest entries] |
| Manifest location | [path in repository] |
| Total tokens seen | [number, per epoch accounting stated] |
| Languages | [list with approximate proportions] |
| Sources | [domains or collection descriptors] |
| Retrieval dates | [dates] |
| Licenses | [license per dataset] |
| Personal data assessment | [finding and basis] |
| Filtering | [summary, with pointer to detail] |
| Deduplication | [method and approximate effect] |
| Contamination checks | [method, and results or "not performed, because…"] |
| Known issues in the data | [quality problems, documented bias, contested provenance] |

Any dataset not listed here was **not** used. Provenance requirements are in
[`DATA_POLICY.md`](DATA_POLICY.md).

## 6. Training procedure

| Field | Value |
| --- | --- |
| Objective | [e.g. causal language modelling] |
| Optimizer | [name, hyperparameters] |
| Learning-rate schedule | [shape, peak, warmup] |
| Batch size | [sequences × tokens] |
| Steps / epochs | [numbers] |
| Precision during training | [format, accumulation behaviour] |
| Hardware | [CPU model, core count, RAM; no GPU unless stated] |
| Wall-clock time | [measured duration, and machine] |
| Seeds | [seed values used] |
| Number of runs | [how many, and which is documented here] |
| Compute cost estimate | [hours, and the basis for the estimate] |
| Code version | [commit hash] |
| Reproducibility status | [reproduced independently / reproduced by author only / not reproduced] |

## 7. Intended use

**Intended:**
- [Research and experimentation on CPU-constrained inference.]
- [Specific tasks the model was evaluated on, each linked to an evaluation section.]

**Not intended:**
- [Production use of any kind.]
- [Safety-critical, legal, medical, financial, or employment decisions.]
- [Anything involving personal data.]
- [Uses requiring factual accuracy.]
- [Surveillance, tracking, or profiling.]
- [Generation of content presented as human-authored without disclosure.]

Any use outside the intended list is unsupported and untested.

## 8. Limitations

State limitations concretely. Generic hedging is not useful.

- [Known failure modes, with examples where possible.]
- [Context length limits and behaviour beyond them.]
- [Vocabulary or tokenizer limits, e.g. scripts or languages poorly represented.]
- [Susceptibility to prompt injection or instruction-following errors.]
- [Tendency to produce confident but incorrect output.]
- [Numeric or arithmetic weaknesses, if measured.]
- [Hardware limits: memory ceiling, speed, architectures not tested.]
- [Behaviour that was not evaluated at all, and is therefore unknown.]

## 9. Evaluation

| Field | Value |
| --- | --- |
| Evaluation suites | [names and versions, with sources] |
| Task categories covered | [list; aim for more than one] |
| Number of runs | [multiple seeds preferred] |
| Reported statistics | [mean, variance, and intervals as measured] |
| Evaluation data separation | [how contamination was avoided] |

### Results

| Task / suite | Metric | This model | Baseline | Conditions | Notes |
| --- | --- | --- | --- | --- | --- |
| [task] | [metric] | [value ± spread] | [value and what the baseline is] | [hardware, precision, prompt format] | [caveats] |

**Baselines used:** [random / trivial / reference system, each with a link or description]

**What these results do not show:** [e.g. general capability, transfer to other tasks, robustness
outside the measured conditions]

**Known confounds:** [measurement noise, prompt sensitivity, small sample size, hardware variance]

Every reported number must be reproducible from a documented command. See
[`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md).

## 10. Hardware compatibility

| Target | Build | Tested | Notes |
| --- | --- | --- | --- |
| 64-bit x86 | [toolchain, flags] | [yes/no, date, scope] | [results, or why untested] |
| 32-bit x86 | [toolchain, flags] | [yes/no, date, scope] | [results — or "not tested", never "supported"] |
| Other | — | no | Not a project target |

- **Compatibility is only claimed for tested configurations**, with the test scope stated.
- Memory figures above must fit the address space of the stated 32-bit configuration, or the model
  is not usable there.
- Behavioural differences between architectures are documented, not normalized away.

## 11. Quantization and variants

| Variant | Storage type | Method | Weight footprint | Quality delta | Measured on |
| --- | --- | --- | --- | --- | --- |
| [e.g. int8] | [type] | [method, e.g. post-training symmetric per-channel] | [MiB] | [measured difference, not claimed] | [hardware] |

- Quantization error must be **measured** against the unquantized variant on the same evaluation,
  not estimated.
- Where quality degradation is unacceptable for a task, say so for that task.
- Mixed-precision or per-layer schemes: [describe or "none"]

## 12. License and provenance

| Item | Value |
| --- | --- |
| Weights license | [exact license, or "not released"] |
| Code license | Apache-2.0 (see [`../LICENSE`](../LICENSE)) |
| Documentation license | [as stated in the repository] |
| Base model or derivative of | [none, or the parent model with its license] |
| Third-party components | [listed in `NOTICE`, or "none"] |
| Redistribution constraints | [any restrictions from data or upstream terms] |

The repository's code license does **not** automatically extend to weights, and vice versa. See
[`LICENSE_POLICY.md`](LICENSE_POLICY.md) §5.

## 13. Known risks

- [Data-related risks: provenance gaps, personal data, biased or harmful content in training data.]
- [Model behaviour risks: hallucination, harmful completions, overconfident errors.]
- [Security risks: if model files are shared, note that loading them is parsing untrusted input.
  See [`SECURITY_MODEL.md`](SECURITY_MODEL.md).]
- [Misuse risks: what the model could be used for that it should not be.]
- [Privacy risks: memorization, if evaluated; otherwise state that it was not evaluated.]

## 14. Ethical considerations

[Two to four sentences on who could be affected, what was done to reduce harm, and what remains
unaddressed. If nothing was done, say that.]

## 15. Distribution and verification

| Item | Value |
| --- | --- |
| Distribution location | [URL, or "not distributed"] |
| Artefact hash (SHA-256) | [hash, or "n/a"] |
| Model format version | [version] |
| Verification instructions | [command or steps] |

## 16. Changelog

| Card revision | Date | Change |
| --- | --- | --- |
| 0 | [date] | Initial card |

---

## Fill-in checklist

- [ ] Every bracketed field replaced or explicitly marked "unknown" / "not applicable"
- [ ] No estimated numbers presented as measurements
- [ ] Baselines named and described
- [ ] Evaluation conditions stated (hardware, precision, prompting)
- [ ] Limitations specific, not generic
- [ ] Hardware compatibility reflects **actual** tests
- [ ] License for weights stated, or the model marked unreleased
- [ ] Known risks listed without minimization
- [ ] Links resolve within this repository
