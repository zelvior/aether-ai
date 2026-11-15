# AETHER — Security Model

This document describes the security concerns the project **anticipates** for its planned
components, and the standards those components will be held to. AETHER has no runtime, parser, or
model today, so this document is a design requirement, not a description of existing defences.

Reporting process: [`../SECURITY.md`](../SECURITY.md).

---

## 1. Trust model

The design assumes the following, in order of centrality:

| Assumption | Consequence |
| --- | --- |
| **Model files are untrusted input.** | A model file may be malformed, truncated, hostile, or crafted to exploit the loader. |
| **Datasets are untrusted input.** | Data may contain malformed content, injected instructions, or malicious payloads aimed at the training pipeline. |
| **The runtime process is not privileged.** | Inference must not require elevated permissions, and must fail safely if it lacks resources. |
| **No network is required.** | The default execution path makes no network calls. Anything that does is opt-in and explicit. |
| **The local machine is the user's.** | No telemetry, no silent uploads, no background data collection. |
| **Dependencies are part of the attack surface.** | Every dependency is a supply-chain decision, and is treated as such. |

A model file is executable-adjacent data. It determines allocation sizes, loop bounds, and tensor
geometry. Treating it as trusted is a vulnerability class, not a shortcut.

## 2. Malicious training data

Threats:

- **Payload-carrying text** aimed at exploiting the tokenizer, the training loop, or a downstream
  tool that opens the corpus.
- **Poisoned samples** intended to bias or backdoor a model's behaviour.
- **Contamination** that makes evaluation results meaningless or misleading.
- **Prompt-injection-style content** in instruction or evaluation data, aimed at whatever consumes
  model output.
- **Traps in parsing paths:** archive bombs, deeply nested structures, enormous single records,
  invalid encodings.

Mitigations required:

- Data is parsed by code that treats every record as hostile: bounded lengths, validated encodings,
  no `eval`, no format auto-detection that executes anything.
- Corpora are scanned for secrets and credentials before use.
- Provenance and manifests are reviewed per [`DATA_POLICY.md`](DATA_POLICY.md), including removal
  procedures.
- Contamination checks against evaluation data are performed and recorded.
- Training runs record the exact dataset version used, so a poisoned run is traceable.

Backdoors and poisoning are **not fully solvable by engineering**. The project does not claim a
model trained on third-party data is free of injected behaviour.

## 3. Unsafe serialization

Prohibited in any artefact the project loads or ships:

- **Pickle** (`pickle`, `dill`, `joblib`) or any format that executes code during load.
- **NumPy object arrays** (`.npy`/`.npz` containing `object` dtype).
- **Arbitrary Python callables** referenced by a checkpoint or a framework's checkpoint format.
- **Shell or eval** in a load, convert, or migrate path, including via subprocess with interpolated
  strings.
- **Formula-bearing or macro-bearing formats** for anything read from disk.

The AETHER model format (planned) is to be a **data-only** format: explicitly typed, length-prefixed
or fixed-layout, with a documented schema, and parsed by dedicated code that validates before it
allocates. See §4.

Serialization must never require deserialization of untrusted code to read weights.

## 4. Model file parsing

The parser is the highest-risk component and is specified accordingly:

- **Validate before allocate.** Every length, dimension, stride, and offset is checked for
  plausibility and for overflow *before* any allocation, and before any arithmetic on it.
- **Overflow-safe arithmetic.** Size and offset computations use checked arithmetic; on 32-bit
  targets, 64-bit intermediates must not be assumed to be available or cheap. Reject rather than
  wrap.
- **Bounded total memory.** The declared tensor sizes must be validated against a configured
  maximum, and the sum of all allocations must stay within a budget. A file cannot request more than
  the process is willing to give.
- **Explicit, versioned schema.** Every field has a defined type, width, and byte order. Unknown
  major versions are rejected; unknown optional fields are skipped by length, never by guessing.
- **Integrity checks.** A checksum over the declared content detects truncation and corruption.
  This is integrity, not authenticity: it does not prove the file came from a trusted source.
- **Truncation and trailing data** are explicit, tested failure modes.
- **Fuzzing.** The parser is a fuzzing target, and a regression corpus of malformed files is kept.
- **Deterministic failure.** A rejected file produces a clear error, no partial state, and no
  uninitialized memory used as data.

## 5. Dependency supply-chain risk

- **Minimal dependencies.** Each one must be justified, per [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
  Fewer dependencies is a security property.
- **Provenance recorded.** Every dependency's source, version, and license is recorded, and pinned
  where practical. See [`LICENSE_POLICY.md`](LICENSE_POLICY.md).
- **Pinned CI actions.** Workflow actions are referenced by version, and permissions are minimized
  (`contents: read` by default).
- **No untrusted input in privileged execution.** Workflow expressions from issues, PR titles, and
  commit messages are never interpolated into shell commands.
- **Build reproducibility** is a supply-chain control: differing builds from identical sources are
  investigated, not ignored.
- **Dependency updates** are reviewed for behaviour changes, not accepted mechanically.

## 6. Memory safety in native inference code

Native code is where most serious vulnerabilities are expected. Requirements:

- **No undefined behaviour** relied upon. Aliasing, alignment, and signed overflow are treated as
  correctness bugs.
- **Bounds checking at boundaries.** All indexing derived from external input is validated; internal
  loops may avoid redundant checks only when the invariant is proven and documented.
- **No unchecked allocation.** Allocation results are checked; failure is handled rather than
  dereferenced.
- **Ownership is explicit.** Who frees what, and when, is documented per module. No ownership by
  convention.
- **No uninitialized reads.** Buffers are initialized or proven fully written before reads.
- **No stack recursion over untrusted depth.**
- **Sanitizer builds** (address, undefined behaviour) are part of the test matrix where available on
  the target.
- **32-bit specifics.** On 32-bit x86 the address space is ~4 GiB and typically much less usable;
  size arithmetic that assumes 64-bit pointers (`size_t` is 32-bit there) must be audited rather
  than assumed portable. Pointer-width truncation is treated as a security bug, not a nuisance.

A single-maintainer project cannot claim formal verification. The standards above reduce the
likelihood of exploitable defects; they do not eliminate them.

## 7. Untrusted input handling

- **All external input is untrusted:** model files, tokenizer assets, configuration, prompts,
  datasets, environment variables, and command-line arguments.
- **No auto-execution.** Opening a file does not trigger code paths that interpret content as code.
- **Resource limits on parsing:** maximum file size, maximum tensor count, maximum vocabulary size,
  and maximum sequence length, all configurable and defaulted conservatively.
- **Denial-of-service is in scope** when it arises from an implementation defect that lets a small
  input consume disproportionate resources.
- **Errors are not silent.** A malformed input produces a clear failure, not a plausible-looking
  guess.

## 8. Reproducible builds

- Builds aim to be deterministic from a recorded toolchain, flags, and source revision.
- Artefacts intended for distribution will publish a hash allowing independent verification.
- Non-reproducible steps (timestamps, environment leakage, nondeterministic linking) are documented
  rather than hidden.
- The 32-bit build, when it exists, is built from the same sources and verified to behave
  equivalently for the same inputs, with deviations documented.

Reproducibility is also an integrity control: it lets someone else confirm that a published binary
corresponds to the published source.

## 9. Privacy

- **Local by default.** No network calls in inference.
- **No telemetry.** No usage statistics, no crash reporting uploads, no identifiers.
- **No silent data collection.** If a future feature needs network access, it is opt-in, documented,
  and off by default.
- **Model outputs are not training data** unless a user explicitly opts in, and no such mechanism
  exists.

## 10. Out of scope for this document

- The safety of model *outputs* — truthfulness, bias, and harmful content — is an evaluation
  concern, not a memory-safety one. Some of it is addressed in
  [`MODEL_CARD_TEMPLATE.md`](MODEL_CARD_TEMPLATE.md) and
  [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md).
- Legal and regulatory compliance.
- Physical security of machines running the software.

## 11. Security review gates

Before a component that parses, allocates, or executes is merged:

- [ ] Threat model updated if the trust boundary changed
- [ ] Malformed-input tests included
- [ ] Allocation and size arithmetic checked for overflow
- [ ] New dependency justified, pinned, and license-checked
- [ ] No prohibited serialization introduced
- [ ] CI permissions unchanged or reduced
- [ ] 32-bit pointer-width implications considered
- [ ] Limitations recorded honestly, including what was not tested

This document is reviewed when a component described here is implemented. Until then, it states
intent, and no security guarantee should be inferred from it.
