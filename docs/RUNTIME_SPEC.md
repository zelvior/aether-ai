# AETHER — Runtime Specification

Status: **Design proposal.** No runtime exists. No kernel is written; no timing is measured. Every memory
figure is arithmetic on a design, cross-referenced to [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md), which is
itself unmeasured.

Related: [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) (what it loads) ·
[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) (what it computes with) ·
[`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) (what it runs on) ·
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §7 (the math it implements)

---

## 1. Scope

The runtime is the only component that executes numerical operations. It performs:

1. Load and validate an `.aether` model file
2. Tokenise input (per [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md))
3. Run the forward pass (prefill + decode)
4. Sample a token
5. Detokenise output

It does **not** orchestrate (`COGNITIVE_SYSTEM_SPEC.md`), retrieve (`KNOWLEDGE_SYSTEM_SPEC.md`), or execute
tools (`TOOLS_SYSTEM_SPEC.md`). Those call it.

### 1.1 Design constraints, in priority order

| # | Constraint | Consequence |
| --- | --- | --- |
| 1 | **Correct** | Reference outputs match a hand-checked implementation |
| 2 | **Safe** | Untrusted files never cause memory unsafety |
| 3 | **Deterministic** | Fixed input + model ⇒ fixed output |
| 4 | **Bounded** | Declared ceilings, enforced |
| 5 | Portable | 32-bit x86 first, no 64-bit assumptions |
| 6 | Fast | **Last**, and only after the above |

**[PROPOSED]** The ordering is load-bearing: a faster kernel that breaks determinism is not a better
kernel, it is a defect.

---

## 2. Model loading

### 2.1 Sequence

```
open ──▶ size check ──▶ header parse ──▶ full validation ──▶ map/read ──▶ bind tensors
         (≤512 MiB)     (MODEL_FORMAT §3)  (MODEL_FORMAT §7)  (§2.2)      (§2.3)
```

**No bytes are read beyond the header until validation succeeds.** This is
[`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) rule F2, and it is why a malformed file cannot cause a
large allocation.

### 2.2 Mapping vs reading

| Strategy | Advantage | Risk |
| --- | --- | --- |
| `read()` into a heap buffer | Simple, portable | Requires one large contiguous allocation |
| `mmap()` read-only | No large allocation; OS pages on demand | Not universal; page-fault latency |

**[PROPOSED]** `mmap` where available, `read()` as fallback. On 32-bit targets the fallback is the risky
path: a contiguous allocation of tens of MiB can fail in a fragmented address space
([`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §5), so the failure must be reported clearly rather
than retried.

### 2.3 Tensor binding

Tensors are bound by **offset into the mapped region**, not copied. This keeps peak memory at roughly
the model size plus activations, which is what [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §5 assumes.

| Check at bind time | Failure |
| --- | --- |
| Offset + size within the data region | `E_BAD_TENSOR` |
| Alignment satisfies the dtype requirement | `E_ALIGNMENT` |
| Shape product matches byte length | `E_BAD_TENSOR` |
| No two tensors overlap | `E_OVERLAP` |

The last check is not paranoia: overlapping tensors would make an in-place update corrupt a neighbouring
weight silently.

---

## 3. Execution model

### 3.1 Two paths, one implementation

| Phase | Shape of work | Dominant cost |
| --- | --- | --- |
| **Prefill** | `T` tokens at once | Matrix–matrix (GEMM) |
| **Decode** | 1 token, growing KV | Matrix–vector (GEMV) |

From [`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §7: Config M prefill is 9.430 GFLOP at
`T = 512`; decode is **18.94 MFLOP per token, independent of context**.

**Decode is a GEMV and therefore memory-bandwidth bound, not compute bound.** Every weight is read once
per token. At 32.14 MiB of `binary32` weights, generating one token reads ≥ 32 MiB from memory. On a
machine with a few hundred MB/s of effective bandwidth, that alone bounds throughput regardless of how
fast the arithmetic is. This is the single most important performance fact about AETHER and it is a
*property of the architecture*, not of the implementation.

### 3.2 Why this makes quantisation attractive

If decode is bandwidth-bound, reducing weight bytes directly increases throughput. int8 storage moves
32.14 MiB → 8.04 MiB ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §4.2), a ~4× reduction in bytes read per
token. Whether that translates proportionally depends on dequantisation overhead — **unmeasured**, and
Phase 8's job to determine.

---

## 4. Memory management

| Requirement | Statement |
| --- | --- |
| `RT-1` | All allocations go through one interface with a tracked budget |
| `RT-2` | Exceeding the declared budget **fails** the request, never degrades silently |
| `RT-3` | No allocation in the decode inner loop after warm-up |
| `RT-4` | Every size is computed with checked arithmetic (64-bit, then narrowed) |

`RT-3` is what makes latency predictable: a `malloc` per token would add jitter and, on 32-bit, a
fragmentation risk that compounds over a long session.

`RT-4` is not boilerplate. [`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §5.1 shows a real computation
from Config M's own dimensions wrapping to **exactly zero** in 32-bit arithmetic, yielding a successful
zero-byte allocation.

### 4.1 The arena

**[PROPOSED]** A single arena for activations, sized at load time from the declared maximum context:

```
arena = weights_peak + kv_cache + activation_peak + scratch + headroom
```

Sized once, never grown. This trades a little memory for the elimination of fragmentation and the
ability to answer "will this fit?" before running.

---

## 5. Kernels

The operations AETHER needs, by importance:

| Kernel | Used by | Notes |
| --- | --- | --- |
| GEMM / GEMV | Every projection | The only one that matters for performance |
| RMSNorm | Every layer | Reduction + scale |
| Softmax | Attention | Max-subtraction required |
| SiLU, sigmoid | SwiGLU | Transcendental — library call |
| RoPE | Attention | Sin/cos table lookup |
| Residual add | Every layer | Memory-bound |

### 5.1 Ordering discipline

The reduction order inside every kernel is **specified, not left to the compiler**
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §6). A kernel that is 20 % faster but sums in a
different order is a different program, and AETHER's equivalence testing would not be able to
distinguish an optimisation from a bug.

**[OPEN]** Whether pairwise summation should be mandatory in the output head, where
`NUMERICAL_STRATEGY.md` §9.2 shows the error is largest (`gamma(8192) = 4.89e-4`).

---

## 6. Threading

| Decision | Status |
| --- | --- |
| Multi-threaded by default | **No** |
| Threading optional | **Deferred** — not proposed for Phase 6 |
| Deterministic under threading | **Unproven** |

Threading a GEMV offers little (bandwidth-bound) and introduces a determinism hazard: floating-point
addition is not associative, so a parallel reduction produces a different result per schedule. AETHER
would have to specify a fixed reduction tree and accept that it may differ from the serial result —
doubling the equivalence matrix ([`PLATFORM_COMPATIBILITY_PLAN.md`](PLATFORM_COMPATIBILITY_PLAN.md) §3).

**[PROPOSED]** Single-threaded until the serial implementation is proven correct and measured. A
deterministic serial baseline is worth more than a fast nondeterministic one.

---

## 7. API surface (conceptual, not code)

| Operation | Input | Output |
| --- | --- | --- |
| `load(path, budget)` | File path, memory budget | Handle or structured error |
| `tokenize(text)` | UTF-8 | Token ids |
| `detokenize(ids)` | Token ids | UTF-8 |
| `prefill(handle, ids)` | Token ids | Updated state |
| `decode(handle)` | — | Next-token logits |
| `reset(handle)` | — | Cleared KV cache |

**No API is specified in detail here.** [`ROADMAP.md`](ROADMAP.md) puts interface design in Phase 6, and
specifying signatures now would be inventing an interface before knowing the implementation's shape.

---

## 8. Error handling

Errors are **structured values**, not strings and not a single errno.

| Category | Examples |
| --- | --- |
| Format | `E_BAD_MAGIC`, `E_BAD_TENSOR`, `E_OVERFLOW` ([`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §8) |
| Resource | `E_OUT_OF_MEMORY`, `E_CONTEXT_EXCEEDED` |
| Numerical | `E_NONFINITE_ACTIVATION` |
| Usage | `E_NOT_LOADED`, `E_BAD_ARGUMENT` |

**No error path leaves the runtime in a half-initialised state.** A failed load frees everything it
allocated; a failed decode leaves the previous state intact so the caller can retry or abort.

---

## 9. Determinism

| Source of nondeterminism | Handling |
| --- | --- |
| Reduction order | Specified per kernel (§5.1) |
| x87 extended precision | `-ffloat-store`, documented (§5.1) |
| SIMD path selection | Fixed per build; recorded in the equivalence report |
| Threading | Absent (§6) |
| Uninitialised memory | All buffers zeroed or fully written before read |
| Pointer-dependent iteration | Forbidden — no iteration over hash-ordered structures |

**[PROPOSED]** Determinism means: same binary, same machine, same input ⇒ **identical** output bytes.
Across builds or machines, output must fall within the tolerance in
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §5.

---

## 10. Resource limits

| Limit | Enforcement |
| --- | --- |
| Model file size | ≤ 512 MiB, checked before read |
| Parameter count | ≤ 10⁹, checked at validation |
| Context | ≤ `T_max` from the model header |
| Arena | Sized at load; never grown |
| Per-request time | Caller-enforced |

Limits come **from the model header where possible**, so a model declares its own requirements and the
runtime refuses to load one it cannot honour.

---

## 11. What the runtime is not

- **Not** a framework. No plugin system, no graph optimiser, no autodiff.
- **Not** a scheduler. One model, one stream.
- **Not** a training engine.
- **Not** general-purpose linear algebra. It implements exactly the kernels AETHER's architecture needs.

Each of those exclusions is a design decision, not an omission: every additional capability is another
place 32-bit behaviour can diverge.

---

## 12. Unresolved questions

1. Is `mmap` reliable across the target platforms, or is `read()` the safer default? **[OPEN]**
2. Should the output head use pairwise summation from the start (§5.1)? **Proposed: yes.** **[OPEN]**
3. Can dequantisation overhead be kept below the bandwidth saving at int8? **Unmeasured.** **[OPEN]**
4. Is a single arena sufficient, or do the KV cache and activations need separate regions? **[OPEN]**
5. What is the arena size formula in practice for Config M at `T = 2048`? **Arithmetic exists; no build.** **[OPEN]**
6. Is `E_NONFINITE_ACTIVATION` recoverable, or must it abort the process? **[OPEN]**
7. Does threading ever become worth the determinism cost? **[OPEN]**

---

## 13. Status summary

| Item | Status |
| --- | --- |
| Load sequence | **Specified** — validate before allocate |
| Mapping strategy | **Proposed** — mmap with read fallback |
| Tensor binding | **Specified** — zero-copy with 4 bind-time checks |
| Prefill / decode split | **Derived** from `ARCHITECTURE_SPEC.md` §7 |
| Decode is bandwidth-bound | **Architectural consequence**, stated §3.1 |
| Kernels | **Enumerated**, none written |
| Reduction order | **Specified** per kernel |
| Threading | **Absent by decision** |
| Determinism | **Required**; cross-build tolerance only |
| Any implementation or measurement | **None.** |
