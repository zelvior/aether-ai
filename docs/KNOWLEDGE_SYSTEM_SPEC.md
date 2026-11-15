# AETHER — Knowledge and Retrieval System

Status: **Design proposal.** No index exists, no corpus ingested, no retrieval measured. All latency and
size figures below are arithmetic on proposed parameters, not measurements.

Related: [`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md) (per-user memory, a different store) ·
[`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) §3 · [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) ·
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2

---

## 1. What problem this solves

AETHER's Core has 8.4 M parameters. It cannot store world knowledge. Even if every parameter were a
fact, that would be fewer facts than a single reference book.

`[S37]` frames the problem exactly: parametric knowledge is hard to update, impossible to attribute, and
cannot be revised without retraining. **Separating knowledge from parameters is not a workaround for a
small model — it is the correct architecture for any model that must cite sources and accept
corrections.**

### 1.1 The knowledge / memory distinction

| | Knowledge | Memory |
| --- | --- | --- |
| Whose | A shared corpus a user ingests | One user's private state |
| Written by | Ingestion, once | The system, per turn |
| Mutable | Only by re-ingesting | By the user |
| Size | Could be large | ≤ 16 MiB |
| Spec | **this document** | [`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md) |

Conflating them creates a privacy problem (shared knowledge leaking into a user profile) and a
correctness problem (user notes treated as authoritative corpus).

---

## 2. The retrieval question, stated honestly

`[S36]` (DPR) reports dense retrieval outperforming strong BM25 by **9–19 points absolute** in top-20
accuracy. That is a large, credible result and AETHER does not dispute it.

**AETHER still proposes BM25-first.** The reasoning is a resource argument, not a quality argument:

| Requirement | BM25 | Dense |
| --- | --- | --- |
| Extra neural parameters | **0** | Encoder, typically 10¹–10² M |
| Encoder storage | **0** | Hundreds of MiB at AETHER's budget scale |
| Query compute | Integer/float ops over postings | One full encoder forward pass |
| Index per document | Postings | Float vector, `d × 4` bytes |
| Training required | **No** | Yes — a second model, under AETHER's constraints |
| Offline capable | **Yes** | Only if the encoder exists locally |
| Updates | Insert postings | Re-encode the document |

**DPR requires a trained dual encoder.** AETHER cannot use a pre-trained one (identity constraint), and
training one is a second model on the critical path. At the 512 MiB working target, an encoder large
enough to be useful would consume a substantial share of the budget
([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2).

### 2.1 When AETHER would be wrong

If retrieval quality proves inadequate on real queries, BM25-first is the wrong choice regardless of its
elegance. The design therefore specifies **hybrid retrieval as the Phase 10 target**, with lexical
first because it can be built and measured immediately.

**[PROPOSED]** AETHER will be judged on retrieval precision/recall against a labelled query set
([`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §2), not on which method it chose.

---

## 3. Ingestion

```
document ──▶ extract ──▶ normalise ──▶ chunk ──▶ tokenise ──▶ index
              (§3.1)      (§3.2)       (§4)      (TOKENIZER)   (§5)
```

Every stage records a manifest entry: source, licence, bytes, hash, timestamp, chunk count.

### 3.1 Text extraction

| Format | Approach | Risk |
| --- | --- | --- |
| Plain text, UTF-8 | Direct | Encoding errors |
| Markdown | Strip syntax, keep structure | Low |
| HTML | Tag strip, entity decode | **Parser is an attack surface** |
| PDF | **Out of scope for Phase 2** | Parser complexity; not worth it initially |
| Binary / unknown | **Rejected** | — |

**[PROPOSED]** AETHER ingests plain text and Markdown only in its first version. PDF extraction pulls in
a parser of considerable complexity for a marginal benefit at this scale, and every parser is an
untrusted-input surface with the same discipline requirements as `MODEL_FORMAT_SPEC.md`.

### 3.2 Normalisation

| Step | Rule |
| --- | --- |
| Encoding | Reject invalid UTF-8; do not guess |
| Unicode | NFC for indexing, **original preserved for display** |
| Case | Fold for indexing, preserve for attribution |
| Script | Do **not** transliterate — Urdu and Hindi are distinct |

The third and fourth rows matter for multilingual work: `TOKENIZER_SPEC.md` §6 forbids normalisation
that would change decoded bytes, and the same rule applies to source text.

---

## 4. Chunking

| Parameter | Proposed | Rationale |
| --- | --- | --- |
| Target chunk | 256 tokens | Fits comfortably in a 2048-token window alongside memory and the turn |
| Overlap | 32 tokens | Reduces boundary loss |
| Boundary preference | Paragraph, then sentence | Semantic coherence |
| Maximum chunks per document | 4,096 | Bounds index growth from one large file |

At 256 tokens with a 224-token stride, a 10,000-token document yields about 45 chunks. Retrieving 3–5
chunks consumes 768–1,280 of the 2,048-token context — **37 % to 62 % of the entire window**, before
memory injection ([`MEMORY_SYSTEM_SPEC.md`](MEMORY_SYSTEM_SPEC.md) §8) or the user's turn.

That is the central tension of retrieval at AETHER's context size and there is no free resolution:
fewer chunks means less evidence, more chunks means less room to answer. At 5 chunks plus 512 tokens
of memory, only about 250 tokens remain for the conversation.

**[OPEN]** The right chunk count is unmeasured and probably task-dependent.

---

## 5. Index

### 5.1 Inverted index

```
term ──▶ [ (doc_id, tf), ... ]      postings, delta-encoded, varint
doc  ──▶ [ (term_id, tf), ... ]     per-document forward list
meta ──▶ offset, length, source, hash
```

| Property | Value |
| --- | --- |
| Structure | Flat arrays, memory-mapped |
| Term dictionary | Sorted array + binary search — **no hash table** |
| Posting encoding | Delta + varint |
| Positions stored | **No** — only term frequencies (BM25 needs no positions) |

Skipping positions roughly halves index size. Phrase queries are sacrificed, which is acceptable: BM25
over unigrams is the stated baseline.

### 5.2 Why a sorted array and not a hash map

A sorted array has no per-entry overhead, is memory-mappable, and binary search over a few hundred
thousand terms is a handful of cache misses. A hash map adds ~16–32 bytes per entry and does not map
cleanly across 32/64-bit boundaries. At AETHER's budget
([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2), the array is simply better.

### 5.3 Size arithmetic

For a corpus of `D` documents, `T` distinct terms, `P` postings:

```
index_bytes ≈  T × (term_len + 4)          term dictionary
             + P × ~2..4                    delta-varint postings
             + D × 16                       document metadata
```

**[PROPOSED]** Bounded by a declared quota, and ingestion **fails** rather than silently exceeding it.

| Corpus | Documents | Terms | Postings | Arithmetic estimate |
| --- | --- | --- | --- | --- |
| Small | 1,000 | 10,000 | 50,000 | ~0.3 MiB |
| Medium | 50,000 | 150,000 | 1,000,000 | ~5 MiB |
| Large | 200,000 | 300,000 | 4,000,000 | ~18 MiB |
| **Declared quota** | 200,000 documents | — | — | **128 MiB cap** |

The quota is a **cap, not an estimate**: at 200,000 documents the arithmetic suggests roughly 18 MiB, so
the 128 MiB cap leaves room for token-identity expansion (Urdu and Hindi produce more distinct terms
than English for the same word count) and for a future hybrid index. The cap exists so ingestion can
**fail loudly** rather than grow without bound.

These are estimates from the formula above, **not measurements.** No corpus has been indexed.

---

## 6. Scoring

BM25 `[S38]`:

```
score(q,d) = Σ_{t∈q} IDF(t) · ( f(t,d)·(k₁+1) ) / ( f(t,d) + k₁·(1 − b + b·|d|/avgdl) )
IDF(t)     = ln( 1 + (N − n(t) + 0.5) / (n(t) + 0.5) )
```

| Parameter | Conventional | AETHER proposal |
| --- | --- | --- |
| `k₁` | 1.2–2.0 | **1.5** |
| `b` | 0.75 | **0.75** |
| `N` | document count | — |
| `n(t)` | docs containing `t` | — |

**[PROPOSED]** Conventional defaults, **untuned**. `[S38]` discusses parameter optimisation; AETHER has
no labelled query set yet, so tuning would be guesswork dressed as calibration.

### 6.1 Determinism

Identical query and index yield identical ranking: scores are computed in a fixed order and ties break
on `doc_id` ascending. No randomness, no approximate structures.

---

## 7. Multilingual retrieval

AETHER targets English, Urdu, Hindi and Roman Urdu. BM25 operates on **terms**, and term identity across
these languages is not free:

| Language | Challenge | Proposed handling |
| --- | --- | --- |
| English | Whitespace tokenised | Standard |
| Hindi | Devanagari; inflected | Light stemming, or none initially |
| Urdu | Perso-Arabic, RTL; inflected | Light stemming, or none initially |
| Roman Urdu | **No standard orthography** — "kya"/"kia"/"kyaa" | **Normalisation table**, §7.1 |

### 7.1 Roman Urdu

The hardest case and the one with no clean solution. Roman Urdu has no standard spelling, so a query for
*kya* will not match a document containing *kia*.

| Approach | Cost | Status |
| --- | --- | --- |
| None | 0 | Baseline — recall will be poor |
| Curated normalisation table | Maintained by hand | **Proposed** for a small high-frequency set |
| Character n-gram indexing | Larger index | **Proposed as fallback** for OOV terms |
| Model-based transliteration | A model | Out of scope |

**[OPEN]** Whether a curated table is maintainable long-term, and how large it must be to matter.

### 7.2 What multilingual retrieval does not imply

Citing a retrieved Urdu passage does not mean the model understood it. Retrieval is lexical; comprehension
is the Core's job, and at 8.4 M parameters that is a genuine limitation.
`TOKENIZER_SPEC.md` §5.4 already states that coverage is not competence; it is restated here because
retrieval makes coverage *look* like competence.

---

## 8. Attribution

Every retrieved chunk carries `(source, offset, hash)`, and every generated claim that uses it should
cite it.

| Requirement | Statement |
| --- | --- |
| `K-1` | Every chunk is traceable to source, offset and hash |
| `K-2` | The system reports **whether** a claim used retrieval |
| `K-3` | The system never presents retrieved text as its own parametric knowledge |

`K-3` is the important one. `EVALUATION_PLAN.md` §7 forbids attributing retrieval success to the model;
this requirement forbids the presentation from implying it.

**[OPEN]** AETHER cannot verify that a citation *supports* the claim — only that the chunk was retrieved.
Claim-level faithfulness checking requires a verifier AETHER does not have. The gap must be documented,
not papered over.

---

## 9. Freshness and updates

| Operation | Mechanism |
| --- | --- |
| Add document | Insert postings; update `N` |
| Delete document | Mark tombstone; **decay requires a rebuild** |
| Update document | Delete + add |
| Rebuild | Deterministic, from manifests alone |

BM25's `IDF` depends on `N` and `n(t)`, so deletions degrade scoring until a rebuild. **[PROPOSED]** A
rebuild is triggered when tombstones exceed 10 % of documents — a simple, stated threshold rather than a
silent quality decay.

---

## 10. Query latency (arithmetic, not measurement)

For a query with `|q|` terms and average posting list length `L`:

```
work ≈ Σ_{t∈q} L(t)   scorings, plus  log T  per term for dictionary lookup
```

A query of 5 terms against a 200,000-document corpus with typical `L` in the low thousands evaluates on
the order of 10⁴ scorings — microseconds to a millisecond of pure arithmetic on any CPU from the last
twenty years.

**But this is arithmetic, not a measurement, and the document says so.** Cache behaviour, memory-mapping
page faults and index layout will dominate, and none has been measured. No latency figure is claimed.

---

## 11. What this system is not

- **Not** a vector database. No embeddings in Phase 2.
- **Not** a knowledge graph.
- **Not** a fact store. It retrieves **passages**, not verified propositions.
- **Not** an answer engine. It supplies evidence; the Core writes prose from it.

---

## 12. Unresolved questions

1. Is BM25-only adequate, or does the DPR result (§2) force dense retrieval sooner? **[OPEN]**
2. What chunk size and count actually work at a 2048-token context? **Unmeasured.** **[OPEN]**
3. Is the 128 MiB index cap the right number against the 512 MiB working target? **[OPEN]**
4. Can Roman Urdu be handled lexically at all (§7.1)? **[OPEN]**
5. Should stemming be applied to Hindi and Urdu, and with what algorithm? **[OPEN]**
6. How should claim-level faithfulness be reported when it cannot be verified (§8)? **[OPEN]**
7. Is 10 % the right tombstone threshold for rebuild? **[OPEN]**

---

## 13. Status summary

| Item | Status |
| --- | --- |
| Knowledge ≠ memory ≠ context | **Specified** |
| Retrieval method | **BM25**, chosen on resource grounds — DPR acknowledged as better quality |
| Encoder required | **None** |
| Ingestion formats | Text and Markdown only; PDF out of scope |
| Chunking | **Proposed** 256/32 — untuned |
| Index | **Proposed** — memory-mapped sorted array, no positions |
| Scoring | **Proposed** — BM25 with conventional untuned parameters |
| Multilingual | **Proposed**, Roman Urdu explicitly unsolved |
| Attribution | **Requirements `K-1`–`K-3`**; faithfulness unverifiable |
| Any implementation or measurement | **None.** |
