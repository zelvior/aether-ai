# AETHER — Memory System Specification

Status: **Design proposal.** Nothing is implemented, nothing is measured. Storage formats described
here do not exist as code.

Related: [`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) · [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md)
(knowledge is separate from memory) · [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) (the memory *budget*, a
different document) · [`DATA_POLICY.md`](DATA_POLICY.md) (governing policy) ·
[`SECURITY_MODEL.md`](SECURITY_MODEL.md)

---

## 1. The three-way distinction this document depends on

Most "AI memory" discussions conflate three things. AETHER separates them because they have different
lifetimes, different privacy properties and different costs.

| | **Context** | **Memory** | **Knowledge** |
| --- | --- | --- | --- |
| Lives in | The model's KV cache, this turn | AETHER's store, across turns | A corpus, read-only |
| Written by | The current session | The system, with consent | Ingested by a user |
| Lifetime | One turn | Until deleted or expired | Permanent until re-ingested |
| Size limit | `T_max` tokens | Explicit quota | Index size budget |
| Addressed by | Position | Explicit API | Retrieval |
| Spec | `ARCHITECTURE_SPEC.md` §4.2 | **this document** | [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) |

**Memory is not context.** Context is what the model sees now; memory is what survives the turn. AETHER
must not describe a long context window as "memory" — a 2048-token window
(`ARCHITECTURE_SPEC.md` §5.1) forgets everything when the session ends.

### 1.1 The absolute constraint

> **Memory must never silently modify Core weights.**

AETHER's Core has no online learning. Weights change only through a documented training run
([`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md)). This is a security property, not an implementation
detail: a model that rewrites its own weights from user input is a model whose behaviour cannot be
audited, reproduced, or rolled back. Stated as requirement **`M-1`**.

---

## 2. Memory types

| Type | Contents | Written by | Retention |
| --- | --- | --- | --- |
| **Working** | Current turn's scratch state | Orchestrator | Discarded at turn end |
| **Episodic** | "On 2026-11-15 the user asked X and got Y" | Explicit commit | Expiring (default) |
| **Semantic** | "The user's project is called AETHER" | Explicit commit | Until deleted |
| **Procedural** | User preferences ("prefers brief answers") | Explicit commit | Until deleted |

**[PROPOSED]** Only three persistent types are distinguished. A richer taxonomy (associative,
prospective, emotional…) is a research aspiration that would add surface area without adding capability
at this scale.

### 2.1 Why episodic memory expires and semantic does not

An episode is a *record*; a fact is a *claim*. Records accumulate without bound and are individually
low-value; facts are few and individually load-bearing. Default retention reflects that asymmetry.

---

## 3. Storage format

### 3.1 Constraints

| Constraint | Reason |
| --- | --- |
| No deserialisation of untrusted data | `MODEL_FORMAT_SPEC.md` §1 — **never pickle**, never `eval` |
| Bounded record size | A memory file is user data and may be attacker-influenced |
| Portable across 32/64-bit | `CPU_32BIT_RESEARCH.md` §5 |
| Human-inspectable | A user must be able to see what is stored |
| Deletable per record | Requirement `M-4` below |

### 3.2 Proposed record layout

A length-prefixed, versioned, line-oriented text format — **not** a database, and **not** a binary
blob:

```
# aether-memory v1
R <id> <type> <created> <expires> <lang> <bytes>
T <text, UTF-8, exactly <bytes> long>
E
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | 64-bit, monotonic | Never reused, so deletion is unambiguous |
| `type` | `epi` / `sem` / `proc` | §2 |
| `created`, `expires` | ISO-8601 UTC, or `-` | `-` means no expiry |
| `lang` | `en`/`ur`/`hi`/`rmu`/`-` | Enables language-scoped retrieval |
| `bytes` | decimal | **Validated against the actual text length** before reading |

**Why text and not binary:** a user can open the file and see exactly what the system remembers. That is
a privacy feature (§7) and it costs only disk space, which is not AETHER's constraint.

**Why the byte count is stored:** it lets a parser reject a truncated or overlong record without
guessing, which is the same class of protection `MODEL_FORMAT_SPEC.md` applies to weights.

### 3.3 Resource bounds

| Limit | Proposed value |
| --- | --- |
| Records total | 4,096 |
| Bytes per record | 4 KiB |
| Total store | 16 MiB |
| Records retrieved per turn | 8 |

**[PROPOSED]** Exceeding any limit fails the *write* with an error, never silently drops a record. A
memory system that quietly forgets is worse than one that refuses.

---

## 4. Retrieval

### 4.1 Why not embeddings

Embedding-based memory retrieval requires an encoder — a second neural network — with its own
parameters, memory footprint, and training requirement. At AETHER's budget
([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §5: 99.55 MiB peak for the Core alone) adding an encoder is a
significant fraction of the whole envelope.

`KNOWLEDGE_SYSTEM_SPEC.md` §4 reaches the same conclusion for document retrieval. Memory is a **smaller**
corpus with a **stronger** recency and type signal, so lexical retrieval is *relatively* stronger here.

### 4.2 The proposed scorer

Deterministic, parameter-free:

```
score(record, query) = w_lex · lexical_overlap
                     + w_rec · recency_decay(created)
                     + w_type · type_prior(record.type)
                     + w_pin · user_pinned
```

| Term | Signal |
| --- | --- |
| `lexical_overlap` | BM25-style term overlap over the record text |
| `recency_decay` | Exponential in age; half-life a documented constant |
| `type_prior` | Procedural > semantic > episodic for preference-shaped queries |
| `user_pin` | Explicit user pin, always wins |

**[PROPOSED]** The weights are **untuned**. They are documented as a starting point to be fitted
against a small labelled set in Phase 6, and must not be described as optimal.

### 4.3 Determinism

Ties are broken by `id` ascending, so identical inputs yield identical retrieval order. This matters:
`EVALUATION_PLAN.md` §5 requires reproducible behaviour, and a nondeterministic retrieval order would
make an output change impossible to attribute to a cause.

---

## 5. Consolidation and conflict

### 5.1 What consolidation is here

**Not** a neural process. Consolidation is a **deterministic pass** that:

1. Merges exact duplicates (same text, same type) keeping the earliest `created`.
2. Collapses episodic records into a semantic summary **only when a template matches** — no model call.
3. Expires records past `expires`.

There is no generative summarisation. A model-generated memory would be a hallucination stored as fact.

### 5.2 Conflict

Two semantic records may contradict ("the project is called AETHER" / "the project is called X").

| Option | Verdict |
| --- | --- |
| Silently overwrite the old | **Rejected** — destroys user data without consent |
| Keep both and hope retrieval sorts it out | **Rejected** — the model will see the contradiction and may pick either |
| Keep both, **surface the contradiction** | **Proposed** |
| Ask the user | **Proposed**, when interactive |

**[PROPOSED]** A contradictory memory pair is reported to the user and **neither is used** until
resolved. Injecting both into context guarantees the model sees a contradiction it cannot reason
about — [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5 is explicit that
reasoning over conflicting input is not a capability this scale has.

---

## 6. Deletion

| Requirement | Statement |
| --- | --- |
| `M-4` | A user must be able to delete any record, and deletion must be complete |
| `M-5` | Deletion must not require rewriting the whole store |
| `M-6` | A deleted record must never reappear through any path |

### 6.1 What "complete" means

| Location | Handled? |
| --- | --- |
| The record line | Deleted |
| Any index / side table | Deleted |
| The context window of an active session | **Requires restart of the session context** |
| A log or audit trail | **Policy decision** — see below |
| A backup or earlier file version | **Outside AETHER's control** |

The fourth row is the honest gap: an audit log that retains deleted content is not deletion. **[OPEN]**
— whether AETHER keeps an audit log of deletions (metadata only, never content) is a policy question
for [`DATA_POLICY.md`](DATA_POLICY.md) and is **not resolved in Phase 2**.

The fifth row is stated because overclaiming deletion is common. AETHER can delete what it controls and
must say what it does not.

---

## 7. Privacy and isolation

| Requirement | Statement |
| --- | --- |
| `M-2` | Memory is per-user and never shared across users |
| `M-3` | Memory content is never sent anywhere off-device |
| `M-7` | Memory is never used to train the Core |

`M-7` deserves emphasis: it forecloses the "your conversations improve the model" pattern entirely.
AETHER has no mechanism to do it, and this requirement makes that a commitment rather than an omission.

### 7.1 Isolation model

Memory lives in a filesystem path scoped to the user and is loaded only for that user's session. There
is no global store, no shared cache, and no cross-user retrieval path. On a shared machine the operating
system's file permissions are the boundary — **AETHER does not add encryption**, and says so.

**[OPEN]** Whether at-rest encryption is in scope. It would protect against another user reading the
file, at the cost of a key-management problem AETHER has no infrastructure for.

---

## 8. Interaction with the Core

Memory reaches the model **only** as text in the prompt, assembled by the orchestrator:

```
[retrieved memory: up to 8 records, ≤ 512 tokens total]
[retrieved knowledge: see KNOWLEDGE_SYSTEM_SPEC.md]
[user turn]
```

| Property | Consequence |
| --- | --- |
| Memory occupies context | Retrieval **reduces** available room for the conversation |
| Retrieval is lossy | A fact not retrieved is a fact the model does not have |
| Injection is bounded | 512 tokens of memory is 25 % of Config M's 2048-token window |

**The third row is a real cost, and it is easy to miss.** Retrieving aggressively starves the actual
conversation. The 512-token cap is a proposed compromise with no measurement behind it. **[OPEN]**

---

## 9. Resource budget

| Component | Proposed limit |
| --- | --- |
| Working memory (per turn) | ≤ 4 KiB |
| Persistent store | ≤ 16 MiB |
| In-RAM index | ≤ 1 MiB |
| Retrieved context per turn | ≤ 512 tokens (≈ 2 KiB of text) |

At 16 MiB the store is 5 % of AETHER's 512 MiB working target — small, but persistent and growing. It is
the only AETHER component whose size increases through normal use, and therefore the only one that needs
a quota at all.

---

## 10. What this system is not

- **Not** a vector database. No embeddings, no approximate nearest neighbour.
- **Not** a knowledge base. Facts about the world belong in [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md).
- **Not** learned. Nothing about retrieval improves with use except by retrieval hitting better records.
- **Not** a context extension. It does not let the model "remember" a 100k-token conversation.

---

## 11. Unresolved questions

1. Are the §4.2 weights meaningfully fittable, or is the design too simple to tune? **[OPEN]**
2. Is 512 tokens of retrieved memory the right share of a 2048-token window? **Unmeasured.** **[OPEN]**
3. Should contradiction detection be lexical only, or is a model call justified? **Proposed: lexical,
   and surface ambiguity rather than guess.** **[OPEN]**
4. Is at-rest encryption in scope (§7.1)? **Maintainer decision.** **[OPEN]**
5. Are deletion audit logs permitted under `DATA_POLICY.md`? **Policy decision, not Phase 2.** **[OPEN]**
6. Does the text format survive 4,096 records without a linear scan being too slow? **Unmeasured.** **[OPEN]**
7. Should memory be scoped per language, or is `lang` only a retrieval hint? **[OPEN]**

---

## 12. Status summary

| Item | Status |
| --- | --- |
| Context / memory / knowledge distinction | **Specified** |
| No weight modification | **Requirement `M-1`** |
| No training on memory | **Requirement `M-7`** |
| Storage format | **Proposed** — length-prefixed text, no binary deserialisation |
| Retrieval | **Proposed** — lexical + recency + type, parameter-free, untuned |
| Consolidation | **Deterministic only**; no generative summarisation |
| Conflict handling | **Proposed** — surface, never silently overwrite |
| Deletion | **Specified** with stated gaps |
| Implementation | **None.** |
