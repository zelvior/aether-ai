# AETHER — Tokenizer Specification

Design: **byte-level BPE**, vocabulary size **8192** (proposed)
Status: **Proposal.** Not implemented. Phase 3 implements this document.

Related: [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §5 (motivation) ·
[`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §7 (container) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §4.1 (embedding)

---

## 1. Requirements

| # | Requirement | Consequence |
| --- | --- | --- |
| T1 | No unknown tokens; every byte sequence is representable | Byte-initialised vocabulary |
| T2 | Encoding is a pure function of bytes and vocabulary version | No sampling at encode time |
| T3 | Decoding is deterministic and never undefined | Documented U+FFFD behaviour |
| T4 | No external dependency, no Unicode tables beyond UTF-8 structure | Implementable in C without ICU |
| T5 | Vocabulary + rules fit 1.6 MiB | [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §3.1 |
| T6 | Encode is `O(n log n)` in input length, with a bounded worst case | No pathological blow-up |
| T7 | Assets are versioned and independently replaceable | Tokenizer version separate from model version |

---

## 2. Why byte-level BPE, and why `V = 8192`

### 2.1 Byte-level initialisation

Following the byte-level BPE approach `[S14]`, the vocabulary begins as the **256 possible byte
values** and merges are learned over byte sequences. Consequences:

- **T1 is satisfied by construction.** Any input — valid UTF-8, invalid UTF-8, binary — is a byte
  string, and every byte is in the vocabulary. There is no "unknown token" path to get wrong.
- **No Unicode normalisation is required.** AETHER does not normalise input. This is a deliberate
  simplification with a real consequence: `"é"` as one code point and as `e` + combining acute are
  *different token sequences*. That is a documented limitation, not an oversight.
- **The cost is longer sequences** for non-Latin scripts, because a multi-byte UTF-8 character is
  several tokens until merges learn it.

### 2.2 Vocabulary size

| `V` | Embedding params at `d=256` | % of Config M | Embedding params at `d=128` | % of Config N |
| --- | --- | --- | --- | --- |
| 4096 | 1 048 576 | 12.4 % | 524 288 | 28.5 % |
| **8192** | **2 097 152** | **24.9 %** | **1 048 576** | **57.0 %** |
| 16384 | 4 194 304 | 49.8 % | 2 097 152 | 114 % — exceeds the model |
| 32768 | 8 388 608 | 99.6 % | 4 194 304 | 228 % |

At `V = 16384` the embedding alone would equal the entire Config M parameter budget. At
`V = 32768` it would double it. This makes vocabulary size a **first-order architecture decision**,
not a tokenizer detail.

`V = 8192` is proposed as the balance point. It is a **proposed value**, and Phase 3 must justify or
revise it with a measured compression ratio on the actual corpus.

**[OPEN]** For Config N, 8192 vocabulary consumes 57.0 % of the parameters. A smaller `V` (4096) may be
correct for Nano specifically. This is a real tension between sharing a vocabulary across
configurations and optimising each one.

### 2.3 Alternatives rejected

| Alternative | Why not |
| --- | --- |
| **Raw bytes** (`V=256`) | Shortest possible code, longest sequences — 1 token per byte quadruples sequence length for Latin text and inflates compute (`O(T)` attention, `O(T·d²)` MLP). Loses most of BPE's compression |
| **Character-level** | Requires Unicode category tables (violates T4) and is not closed over arbitrary input (violates T1) |
| **Word-level** | Unbounded vocabulary, OOV problem — the thing `[S11]` exists to solve |
| **Unigram / SentencePiece** `[S12][S13]` | Viable, and arguably better compression. Rejected for **implementation cost**: unigram needs a Viterbi search, a unigram probability table, and a more complex trainer, versus BPE's greedy merge loop. Revisit in Phase 3 if compression is inadequate |

---

## 3. Special tokens

| ID | Name | Meaning |
| --- | --- | --- |
| 0 | `<\|unk\|>` | **Present but never produced by encoding.** Reserved so that ID 0 is not a data token |
| 1 | `<\|bos\|>` | Beginning of sequence |
| 2 | `<\|eos\|>` | End of sequence |
| 3 | `<\|pad\|>` | Padding (training batches only) |
| 4 | `<\|eot\|>` | End of turn (reserved; unused in v1) |
| 5 | `<\|reserved0\|>` | Reserved, must not appear in training data |
| 6–31 | — | **Reserved range.** Encoder must never emit `0 … 31` from data |

Because the vocabulary is byte-initialised, data tokens occupy `32 … 8191`, leaving
**8160 data tokens** and 32 fixed specials.

**[PROPOSED]** `<|unk|>` exists for format completeness and is never emitted. Its presence makes the
"no unknown token" claim checkable: a test asserts that encoding arbitrary bytes never produces ID 0.

Reserving `0 … 31` also means a token ID in that range in a model file or a prompt is **always** a
special, never a data token — which makes some classes of injection bug detectable.

---

## 4. Encoding algorithm

### 4.1 Overview

```
encode(bytes):
  1. Validate the configuration and vocabulary version.
  2. symbols ← the input bytes, each as a token ID in 256 … 511  (byte b → 256 + b)
  3. For each merge (a, b) in vocabulary order:
       scan left-to-right, replacing every adjacent (a, b) with the merged ID
  4. Return symbol IDs.
```

Byte values map to IDs `256 … 511`. IDs `32 … 255` are reserved for *learned* merges of a single
byte (none exist in v1, but the space is defined) — this keeps the byte→ID mapping arithmetic and
therefore impossible to get wrong: `id = 256 + byte`.

### 4.2 Merge application order

**[PROPOSED] T-P1. Merges are applied in a single left-to-right pass per merge rule, and rules are
processed in the order they appear in the vocabulary file.**

This is the standard BPE formulation `[S11]`. The details that must be pinned down, because different
libraries disagree on them:

| Detail | AETHER rule |
| --- | --- |
| Overlapping candidates (`aaa` with rule `aa`) | Leftmost-first, **non-overlapping**: `aaa` → `aa`, `a` |
| Rule applied across the whole string at once, or one occurrence at a time? | Whole string, left to right, non-overlapping |
| Ties between two rules applicable at the same position | Lower rule index wins |
| Re-scan after a merge creates a new candidate | **Yes** — the pass continues from one position back |

Without these rules stated explicitly, two "BPE" implementations produce different token sequences for
the same text and the same vocabulary. That would break T2 across implementations.

### 4.3 Complexity and worst case

Naive implementation is `O(n · M)` for input length `n` and `M` merges — at `n = 4096` and `M = 8160`
that is ~33 M comparisons per encode, which is borderline.

**[PROPOSED] T-P2. Implement with a linked list over positions plus a priority queue of candidate
pairs**, giving `O(n log n)` typical behaviour. The naive version is the correctness reference; the
fast version must produce identical output on a fuzz corpus.

**Bounded worst case.** Input length is capped at `MAX_INPUT_BYTES` (default 1 MiB, configurable,
enforced *before* tokenisation). A token-count cap also applies: if encoding yields more than
`MAX_TOKENS` (default `T_max = 2048`) the encoder returns `E_TOO_LONG` rather than truncating
silently. Silent truncation is a correctness bug that appears as a mysterious quality drop.

---

## 5. Vocabulary file format

Embedded in the model container as the Tokenizer Block
([`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §7). Canonically described as JSON for tooling, but
**the shipped artefact is binary**.

### 5.1 Logical content

```
{
  "version": 1,
  "type": "byte-bpe",
  "vocab_size": 8192,
  "n_special": 32,
  "byte_token_base": 256,
  "merges": [ [a, b], ... ],          // length = vocab_size - 512
  "tokens": { "<id>": "<base64 bytes>" },   // for inspection only
  "flags": { "normalize": false, "add_prefix_space": false }
}
```

Constraint: `n_special + 256 (bytes) + n_merges == vocab_size`.

### 5.2 Binary layout

As defined in [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §7, with these additional invariants:

| Invariant | Check |
| --- | --- |
| Offset table monotonic, first `0`, last `== strings_size` | Loader rejects otherwise |
| `vocab_size` in TB equals `arch.vocab_size` in AMB | Loader rejects otherwise |
| `n_merges` equals `vocab_size − 512` | Loader rejects otherwise |
| Every merge operand `< 512 + merge_index` | Rejects forward references / cycles |
| Merge targets are unique among data tokens | Rejects ambiguity |
| `max_token_len ≤ 255` | Bounds per-token buffer |
| Total TB size ≤ 8 MiB | [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §12 |

**"No forward references"** is the key structural rule: merge `i` may only reference tokens created
before `i`. This makes cycles impossible by construction and makes decoding well-founded.

### 5.4 What vocabulary coverage does and does not mean

This subsection exists because it is cited from four documents and because the distinction it draws is
the easiest thing in the project to overstate.

| Claim | What it requires | AETHER status |
| --- | --- | --- |
| **Encoding coverage** | `decode(encode(s)) == s` for text in the script | Testable in Phase 3 |
| **Compression parity** | Similar bytes-per-token across languages | Requires a measured corpus |
| **Capability** | The model understands and generates the language | Requires a trained model |
| **Fluency** | Output is natural to a native speaker | Requires human evaluation |

**A tokenizer that encodes Devanagari without error has demonstrated the first row and nothing else.**

The gap between rows 1 and 3 is where most multilingual claims go wrong. A vocabulary that covers Urdu
means AETHER can *represent* Urdu text, not that it can *respond* in Urdu. At `V = 8192` with 57 % of
Config N's parameters in the embedding table ([`MULTILINGUAL_RESEARCH.md`](MULTILINGUAL_RESEARCH.md)
§4.4), the vocabulary is a representation decision, not a capability decision.

**Therefore:** any AETHER document claiming a language is supported must state which of the four rows it
is claiming. `MULTILINGUAL_RESEARCH.md` §9 lists the five things a real multilingual result would have to
show.

---

## 6. Decoding

### 6.1 Algorithm

```
decode(ids):
  for each id:
    if id is special: emit nothing (or a documented marker) — see §6.2
    else: append the token's byte string to the output buffer
  return the byte buffer
```

Decoding is a concatenation. There is no inverse-merge search: the vocabulary stores the **byte string**
for each token, so decoding is `O(total bytes)` and cannot fail. This is a deliberate design choice —
storing byte strings costs about 1 MiB ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §3.1) and removes an
entire class of decoder bugs.

### 6.2 Special tokens on decode

| Token | Decode behaviour |
| --- | --- |
| `<\|bos\|>`, `<\|pad\|>`, `<\|reserved*\|>` | Emit nothing; ignored |
| `<\|eos\|>` | Stop decoding; emit nothing |
| `<\|unk\|>` | Emit U+FFFD (`EF BF BD`); should never occur |

**[PROPOSED]** Specials are **not** rendered as text. A caller that wants to display them must handle
them itself. This keeps round-trip semantics clean: `decode(encode(s)) == s` for all byte strings `s`
that contain no token-ID sequence forbidden by §6.3.

### 6.3 Invalid UTF-8

The tokenizer operates on bytes, so it never rejects invalid UTF-8. Whether the *output* is valid UTF-8
depends on the input bytes and the token strings.

| Situation | Behaviour |
| --- | --- |
| Input is invalid UTF-8 | Encodes and decodes losslessly as bytes. **Not an error** |
| Output contains invalid UTF-8 | Preserved as bytes. A caller that requires text validates it |
| A byte stream is truncated mid-character | Preserved; it is just bytes |

**[PROPOSED]** The tokenizer guarantees **byte-level round-trip**, not Unicode-level round-trip. That
guarantee is strong, simple, and testable:

```
for all byte strings s: decode(encode(s)) == s
```

This is stated as a hard invariant with a property test in Phase 3, and it is the reason no Unicode
normalisation is performed (§2.1).

---

## 7. Determinism

| Source of divergence | Rule |
| --- | --- |
| Merge order | Fixed by vocabulary order, not by frequency at encode time |
| Ties | Lower merge index wins (§4.2) |
| Hash iteration | **No hash tables in the encoder's decision path.** Lookups use sorted arrays or direct indexing |
| Locale | Never consulted. `tolower`, `isalpha`, locale-dependent comparisons are **forbidden** in tokenizer code |
| Threading | Encoder is pure and reentrant; no shared mutable state |
| Platform | Byte-level operations only; no `char` signedness dependence (`unsigned char` everywhere) |

**[PROPOSED] T-P3.** A conformance test asserts that encoding a fixed corpus of ~10 000 strings
produces a **committed hash** of the token-ID sequence. Any change to the encoder that alters output
for a fixed vocabulary fails the test. Changing behaviour requires bumping `tok.version`.

---

## 8. Resource requirements

| Resource | Bound | Basis |
| --- | --- | --- |
| Vocabulary byte strings | ≤ 1.00 MiB | Mean token ≈ 8 B × 8192, plus length prefixes |
| Offset table | 32 KiB | `(8192+1) × 4` |
| Merge table | 60 KiB | `8160 × 8` bytes (two `u32`, or two `u16` if IDs < 65536) |
| Special-token table | 1 KiB | 32 entries |
| Encoder working memory | `O(n)` over input | Linked list + priority queue |
| Peak encoder memory | ≤ 8 × input length | Positions, IDs, queue entries |

At the 1 MiB input cap, encoder working memory is bounded at ~8 MiB — acceptable, and it is included
in the runtime overhead budget ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.3 gives 1 MiB for the
tokenizer, which is **insufficient for a 1 MiB input**; see §10 question 3).

---

## 9. Training the vocabulary (Phase 3)

Not implemented in Phase 2. The procedure Phase 3 must follow:

1. **Corpus selection** per [`DATA_POLICY.md`](DATA_POLICY.md): manifest, provenance, license,
   permission basis recorded **before** any tokenizer training run.
2. **Pre-tokenisation decision** recorded: AETHER proposes **none** (raw byte stream), matching
   `[S11]`'s character-level formulation and avoiding language-specific rules.
3. **Deterministic merge learning**: ties broken by a documented rule (e.g. lexicographic on the pair),
   so two runs on the same corpus produce the same vocabulary.
4. **Voice/vocabulary provenance**: the resulting `tok` asset is a **derivative of the corpus** and its
   licensing is governed by [`LICENSE_POLICY.md`](LICENSE_POLICY.md) §2. This is not resolved by
   assuming the corpus license covers the tokenizer asset. **[OPEN]** — depends on the unresolved
   maintainer decision on tokenizer-asset licensing.
5. **Reported statistics**: compression ratio (bytes/token) per corpus split, coverage of scripts,
   number of tokens at maximum length, and the share of vocabulary consumed by merges that occur
   fewer than *N* times.

---

## 10. Unresolved questions

1. **Is `V = 8192` right**, given it is 25 % of Config M and 57 % of Config N? **[OPEN]** — Phase 3
   measures compression vs parameter cost.
2. **Should Config N use a separate, smaller vocabulary?** That doubles the tokenizer assets and forks
   the pipeline. **[OPEN]**
3. **The tokenizer memory budget in [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.3 (1 MiB) is too small**
   for the 1 MiB input cap with an `O(n)` encoder. Either the input cap drops to ~128 KiB or the
   budget rises to ~8 MiB. **Proposed: raise the runtime overhead budget to 10 MiB, keep the 1 MiB
   cap.** **[OPEN]** — this is a cross-document inconsistency found while writing this spec and must
   be resolved before Phase 3.
4. **No Unicode normalisation** means `"é"` (U+00E9) and `"e"` + U+0301 tokenise differently. Is that
   acceptable for AETHER's intended corpus? **Proposed: yes**, documented as a limitation. **[OPEN]**
5. **Is BPE's greedy segmentation adequate**, or is the unigram/Viterbi approach `[S12]` worth its
   implementation cost? **[OPEN]**
6. **Tokenizer-asset licensing** is unresolved and blocks training a vocabulary on external data
   ([`LICENSE_POLICY.md`](LICENSE_POLICY.md) §2, §7). **[BLOCKED on maintainer decision]**
