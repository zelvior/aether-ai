# AETHER — Multilingual Research

Status: **Analysis and proposal.** No tokenizer has been trained, no corpus measured, no compression
ratio observed. Every number here is derived from UTF-8 encoding rules and tokenizer arithmetic, not
from a measurement of text.

Related: [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) (the tokenizer itself) ·
[`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §8 (data balance) ·
[`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) §7 (multilingual retrieval) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5 (parameter cost of vocabulary)

---

## 1. The problem this document addresses

AETHER targets English, Urdu, Hindi and Roman Urdu on a **2048-token context** and an **8192-token
vocabulary**. Those are severe constraints for a multilingual system, and they interact in ways that
are easy to miss.

This document asks one question precisely:

> **Given a fixed vocabulary and a fixed context window, what does each target language actually cost,
> and what is the least-bad allocation?**

It does not answer "can AETHER speak Urdu well?". That is a model-capability question
([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §5.4), and coverage is not competence.

---

## 2. The four targets, and why three of them are different problems

| Language | Script | Direction | UTF-8 bytes/char | The hard part |
| --- | --- | --- | --- | --- |
| English | Latin | LTR | **1** | Nothing — the easy case |
| Hindi | Devanagari | LTR | **3** | Conjuncts; 3 bytes per base character |
| Urdu | Perso-Arabic | **RTL** | **2** | Right-to-left handling; no standard transliteration |
| Roman Urdu | Latin | LTR | **1** | **No standard orthography** |

**[ESTABLISHED]** the byte costs — they follow from UTF-8's definition:
ASCII is 1 byte, U+0800–U+FFFF is 3 bytes (Devanagari U+0900–U+097F), U+0080–U+07FF is 2 bytes
(Arabic U+0600–U+06FF).

The fourth row is the one with no clean solution and it is discussed separately in §6.

---

## 3. What "one token" costs per script

A byte-level BPE tokenizer (per [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §4) starts from raw bytes and
merges frequent pairs. **Before merges, a character occupies as many tokens as it has UTF-8 bytes.**

| Script | Bytes/char | Characters that fit in 2048 tokens *before merges* |
| --- | --- | --- |
| English | 1 | 2,048 |
| Urdu | 2 | 1,024 |
| Hindi | 3 | **682** |

**Hindi is three times more expensive per character than English.** A context that holds an English
paragraph holds roughly a third of the equivalent Hindi paragraph.

### 3.1 Devanagari conjuncts make it worse

Devanagari combines consonants with a virama (U+094D) to form conjuncts. The conjunct *ksha* (क्ष) is
three code points:

```
क  U+0915  (3 bytes)
्   U+094D  (3 bytes)
ष  U+0931  (3 bytes)
              = 9 bytes
```

A single visually-single glyph is **9 bytes** — nine tokens before any merge. A model given only 2048
tokens and a Hindi document will run out of context very quickly unless the merge table learns these
clusters.

**[ESTABLISHED]** the encoding arithmetic.
**[PROPOSED]** that BPE merges will capture common conjuncts; **unverified**, and it depends entirely on
merge-table allocation (§4).

### 3.2 Urdu and Arabic shaping

Perso-Arabic letters take initial, medial, final and isolated forms depending on position. Crucially,
**this is a display concern, not an encoding concern**: the stored code points are the same base letters
regardless of how they render.

That means Urdu's byte cost is stable and predictable (2 bytes/char) — unlike Hindi, whose conjunct
behaviour genuinely changes storage. The Urdu-specific risk is **normalisation** (§5), not encoding.

---

## 4. Vocabulary allocation under a fixed budget

This is the central quantitative question, and it has a counter-intuitive answer.

### 4.1 The merge budget

```
V = 8192,  specials = 32  ⇒  merges available = 8,160
```

Each merge is learned from adjacent pairs in the **training corpus**. A merge learned on Latin text
cannot compress Devanagari — the byte pairs do not occur. **Merge tables are script-specific and the
split must be decided in advance**, because BPE applied naively to a corpus dominated by English will
spend nearly all 8,160 merges on English.

### 4.2 What a naive proportional split produces

Suppose the corpus is 50 % English, 20 % Hindi, 20 % Urdu, 10 % Roman Urdu by bytes, and merges are
allocated proportionally:

| Language | Bytes/char | Merge share | Merges | Bytes covered per merge |
| --- | --- | --- | --- | --- |
| English | 1 | 50 % | 4,080 | **1.0** |
| Hindi | 3 | 20 % | 1,632 | **3.0 (favourable)** |
| Urdu | 2 | 20 % | 1,632 | 2.0 |
| Roman Urdu | 1 | 10 % | 816 | 1.0 |

**Read the "bytes covered per merge" column carefully — it inverts the usual intuition.** Hindi gets
*fewer* merges but each one covers *more* bytes, because Devanagari characters are already multi-byte.
A proportional split is therefore **not** as unfair to Hindi as it first appears.

The unfairness is elsewhere: Hindi starts at 682 characters per 2048-token window, so it needs **more**
merges to reach parity in *characters* — but each merge buys more. **[OPEN]** Whether these effects
cancel is not something arithmetic can settle; it requires measuring compression on real text.

### 4.3 The allocation AETHER proposes

**[PROPOSED]** Fixed per-script merge quotas rather than proportional allocation, because proportional
allocation lets the dominant language starve the others and the split is not adjustable after training.

| Script | Proposed merges | Rationale |
| --- | --- | --- |
| Latin (English + Roman Urdu combined) | 4,000 | Shared byte alphabet; merges largely transfer |
| Devanagari (Hindi) | 2,400 | Highest bytes/char; needs conjunct coverage |
| Perso-Arabic (Urdu) | 1,760 | 2 bytes/char; simpler combining than Devanagari |

Combining English and Roman Urdu into one Latin quota is a genuine efficiency: both are ASCII, so a
merge like `th` serves both. This is the single most useful allocation insight available without
measurement.

**[OPEN]** These quotas are a starting point with no empirical basis. They must be revised after
measuring compression on a real four-language corpus — which does not exist yet.

### 4.4 The parameter cost of this decision

Vocabulary is not free in AETHER — it is the largest single tensor in Config N.

| `V` | Config N parameters | Embedding share |
| --- | --- | --- |
| 4,096 | 1,315,968 | 39.8 % |
| **8,192** | **1,840,256** | **57.0 %** |
| 16,384 | 2,888,832 | 72.6 % |

Doubling the vocabulary to improve Devanagari coverage would consume **three quarters** of Config N's
parameters in a lookup table. This is why the answer to "can AETHER support more languages" is not
simply "use a bigger vocabulary" — at `d = 128` the vocabulary is already the dominant cost.

---

## 5. Normalisation

`TOKENIZER_SPEC.md` §6 forbids normalisation that would change decoded bytes, requiring
`decode(encode(s)) == s` exactly.

### 5.1 The Urdu case

Urdu has real orthographic variation that is tempting to normalise:

| Variation | Example | Why it tempts |
| --- | --- | --- |
| Arabic vs Urdu yeh | ي (U+064A) vs ی (U+06CC) | Visually near-identical |
| Arabic vs Urdu kaf | ك (U+0643) vs ک (U+06A9) | Different letters, often confused |
| Zero-width non-joiner | U+200C present or absent | Changes effective word |
| Diacritics (harakat) | Usually omitted | Optional in normal writing |

**AETHER does not normalise any of these**, because normalising breaks the round-trip guarantee: the
decoder cannot know whether to emit `ي` or `ی`. That is the correct call for correctness and the wrong
call for compression, since it forces the model to learn both spellings as separate tokens.

**[PROPOSED]** Keep raw bytes; treat the loss as a documented cost. `[OPEN]` — an
index-time-only normalisation for *retrieval* (not encoding) could recover some of it without breaking
the round trip, and deserves assessment in Phase 3.

---

## 6. Roman Urdu: the genuinely unsolved case

Roman Urdu is Urdu written in Latin script, and **it has no standard orthography**. The same word may
appear as:

```
kya, kia, kyaa, kiya       "what"
nahi, nai, nahin, nahī      "no / not"
aap, ap, aap                "you"
```

This is not a spelling-error problem that can be corrected — there is no correct spelling to correct to.
Every variant is legitimate.

### 6.1 Why this is hard for a tokenizer

BPE learns only what it sees. With 4,000 Latin merges shared between English and Roman Urdu, and Roman
Urdu being a small fraction of the corpus, most variants will not be merged and will decompose into
individual characters — inflating sequence length exactly where context is scarcest.

### 6.2 Options, with honest assessments

| Approach | Effect | Cost | Verdict |
| --- | --- | --- | --- |
| Do nothing | Poor compression; model learns variants separately | none | Baseline |
| Curated variant table | Merges the frequent variants into one token | Hand-maintained forever | **Proposed**, for a small high-frequency set |
| Character n-gram features | Tolerates unseen variants | Larger vocabulary, dilutes merges | Considered, deferred |
| Transliterate to Perso-Arabic | Makes it "Urdu" | **Destroys the user's text**; illegal for chat | **Rejected** |
| Model-based normalisation | Best quality | A model; unaffordable | Out of scope |

**The transliteration row is rejected on principle, not cost.** Users write Roman Urdu because they
want to; converting their text violates `decode(encode(s)) == s` and would make the system misrepresent
what it was given.

**[OPEN]** Whether a curated table is maintainable at all is unknown, and it is the kind of task that
looks small at the start and never ends.

---

## 7. What multilingual coverage does and does not mean

This section exists because it is the easiest claim in the project to overstate.

| Claim | Meaning | Evidence required |
| --- | --- | --- |
| **Encoding coverage** | The tokenizer accepts the script without error | A test: `decode(encode(s)) == s` |
| **Compression parity** | Similar tokens-per-character across languages | Measured compression per language |
| **Capability** | The model understands and generates the language | An evaluation with held-out data |
| **Fluency** | Output is natural to a native speaker | Human evaluation |

**AETHER will have the first from Phase 3.** The second requires a corpus. The third and fourth require a
trained model and a benchmark that does not currently exist for Roman Urdu at all.

`TOKENIZER_SPEC.md` §5.4 makes this point; it is restated because a tokenizer that handles Devanagari
*looks like* multilingual competence and is not.

---

## 8. Data availability, honestly

The hardest constraint on multilingual AETHER is not algorithmic.

| Language | Public corpora | Licence clarity | AETHER position |
| --- | --- | --- | --- |
| English | Abundant | Varies; some clean | Obtainable |
| Hindi | Moderate | Often unclear | **`[OPEN]`** — needs licence review |
| Urdu | Scarce | Often unclear | **`[OPEN]`** — likely limiting |
| Roman Urdu | **Very scarce** | Almost always unclear | **Likely unavailable** |

No dataset is downloaded or included in Phase 2, per [`DATA_POLICY.md`](DATA_POLICY.md). This table
records a **risk**, not a plan: [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §8 already flags
an 84 M-token corpus as the critical path, and that was for English.

**[OPEN]** Whether adequate Urdu and Roman Urdu data with defensible provenance exists at all. If it
does not, the honest outcome is that AETHER supports tokenization but not capability in those
languages — and the model card must say so.

---

## 9. What a multilingual result would have to show

To claim "AETHER handles Urdu", all of the following are required:

| # | Requirement |
| --- | --- |
| 1 | Round-trip equality on a held-out Urdu corpus |
| 2 | Measured compression ratio within a stated factor of English |
| 3 | A held-out evaluation with an Urdu-capable baseline |
| 4 | Reported per-language, never averaged into a single "multilingual score" |
| 5 | Roman Urdu reported **separately**, never merged into Urdu |

The fifth is important: Roman Urdu and Urdu are different problems and averaging them hides both.

---

## 10. Unresolved questions

1. What compression ratio does each script actually achieve at `V = 8192`? **Requires a corpus.** **[OPEN]**
2. Are the §4.3 quotas defensible, or does Devanagari need more? **Untested.** **[OPEN]**
3. Is Urdu normalisation worth breaking the round-trip guarantee? **Proposed: no.** **[OPEN]**
4. Can a Roman Urdu variant table be maintained, and how large must it be? **[OPEN]**
5. Does sufficient Urdu or Roman Urdu data with clean provenance exist (§8)? **May be project-limiting.** **[OPEN]**
6. Should retrieval (not encoding) normalise Urdu orthography to improve matching? **[OPEN]**
7. Is right-to-left output rendering a runtime concern or purely a display concern? **Proposed: display — the token stream is code points, not visual order.** **[OPEN]**

---

## 11. Status summary

| Item | Status |
| --- | --- |
| UTF-8 byte costs per script | **Established** — follows from the standard |
| Devanagari conjunct cost (9 bytes) | **Established** arithmetic |
| Urdu shaping is display-only | **Established** |
| Merge allocation per script | **Proposed**, no empirical basis |
| Latin merging of English + Roman Urdu | **Proposed** — the one clear efficiency |
| Vocabulary cost of more languages | **Exact arithmetic** — 57 % at `V=8192`, `d=128` |
| Normalisation policy | **Proposed** — none, to preserve round-trip |
| Roman Urdu | **Unsolved**, with options assessed and one rejected on principle |
| Coverage vs capability | **Separated explicitly** (§7) |
| Any corpus, measurement, or tokenizer | **None.** |
