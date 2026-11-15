# AETHER — Memory Budget

Status: **Proposal.** All figures are **derived analytically** from the architecture in
[`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md). **None is measured.** No AETHER binary exists to
measure.

This document is the arithmetic behind every memory claim in the project. If a number appears
elsewhere without a derivation, it should be traceable to this file.

---

## 1. Why a memory budget document exists

On a 32-bit target, memory is the constraint that decides what is possible. A model that is merely
slow can still run; a model that does not fit cannot run at all, and the failure is often an
allocation error rather than a graceful degradation. AETHER therefore fixes budgets **before** writing
code, so that implementations are written to a target rather than discovering one.

---

## 2. The budget envelope

### 2.1 Address-space budget

| Quantity | Value | Basis |
| --- | --- | --- |
| Nominal 32-bit VA | 4 GiB | Architectural maximum |
| Typical user-mode VA, Linux i386 | ~3 GiB | Standard `PAGE_OFFSET` split |
| Typical user-mode VA, Windows 32-bit | 2 GiB | Default (without `/3GB` + `LARGEADDRESSAWARE`) |
| **AETHER design budget** | **2 GiB** | Conservative case, adopted deliberately |
| **AETHER runtime working target** | **≤ 512 MiB** | Leaves 1.5 GiB of headroom for fragmentation, OS, and user processes |

The 2 GiB figure is chosen because **the design must hold on the least favourable common
configuration**. Designing to 3 GiB and discovering the 2 GiB case later is how portability claims
become untestable.

**[ASSUMPTION]** That 2 GiB is the right conservative figure for AETHER's target population. This is
a judgement, not a measurement, and Phase 7 should verify it against at least one real 32-bit
environment.

### 2.2 Why 512 MiB, not 1.9 GiB

A runtime that consumes 1.9 GiB of a 2 GiB address space is theoretically possible and practically
fragile: fragmentation over a long uptime, a large contiguous allocation, or a mapped file can turn a
working configuration into a failure. A 512 MiB working target keeps the design robustly inside the
envelope. §5 shows the actual requirement is far below even this.

### 2.3 No claim

**No 32-bit compatibility is claimed.** These budgets describe what the design is *intended* to fit.
Nothing has been built. See [`ROADMAP.md`](ROADMAP.md) Phase 7.

---

## 3. Budget 1 — Model storage (on disk, in the format)

Parameters `P`, bytes per parameter `bpp`:

| Config | Parameters | `binary32` (4 B) | int8 (1 B) | int4 (0.5 B) |
| --- | --- | --- | --- | --- |
| Config T (Test) | 228 672 | 0.87 MiB | 223.31 KiB | 111.66 KiB |
| Config N (Nano) | 1 840 256 | 7.02 MiB | 1.76 MiB | 898.56 KiB |
| Config M (Micro) | 8 425 728 | 32.14 MiB | 8.04 MiB | 4.02 MiB |

Plus tokenizer assets and container overhead, bounded in §3.1.

### 3.1 Non-weight storage

| Item | Proposed bound | Basis |
| --- | --- | --- |
| Vocabulary: token strings | ≤ 1.00 MiB | `V = 8192`, mean token ≈ 8 bytes, plus length prefixes |
| Vocabulary index tables | ≤ 64 KiB | `V × 4` bytes offset table |
| Merge rules (BPE) | ≤ 512 KiB | `V × 8` bytes worst case |
| Metadata / header | ≤ 64 KiB | [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §3 |
| Integrity records | ≤ 16 KiB | Per-tensor digests |
| **Total non-weight** | **≤ 1.60 MiB** | Sum of the above bounds |

### 3.2 Total model storage

| Config | Weights (`binary32`) | Non-weight | **Total** |
| --- | --- | --- | --- |
| Config T | 0.87 MiB | ≤ 1.60 MiB | **≤ 2.47 MiB** |
| Config N | 7.02 MiB | ≤ 1.60 MiB | **≤ 8.62 MiB** |
| Config M | 32.14 MiB | ≤ 1.60 MiB | **≤ 33.74 MiB** |

Both are trivially small. **Storage is not a constraint for AETHER.** It is included for completeness
and because Phase 8 quantisation changes it.

---

## 4. Budget 2 — Runtime memory (residency during inference)

Inference residency has four components:

1. **Weights** — resident, read-mostly.
2. **KV cache** — grows with context, fixed at allocation by `T_max`.
3. **Transient buffers** — score buffer, MLP buffer, activations, logits row.
4. **Runtime overhead** — allocator metadata, code, stack.

### 4.1 KV cache

With sliding-window attention, a correct implementation need only retain `W` keys and values per layer,
not the full context — the cache is a **ring buffer of size `W`**. But retention policy is an
implementation choice, and retaining the full context up to `T_max` is the simpler, safer default. Both
are budgeted:

| Policy | Formula (per layer) | Config M, `binary32`, `T_max = 2048` |
| --- | --- | --- |
| Ring buffer of `W` | `2 · W · d · bpp` | `2 × 256 × 256 × 4 = 512 KiB` × 8 = **4.00 MiB** |
| Full context | `2 · T_max · d · bpp` | `2 × 2048 × 256 × 4 = 4.00 MiB` × 8 = **32.00 MiB** |

The full-context figure is used for budgeting, because budgeting the optimistic case is not a budget.

**[PROPOSED]** The runtime retains full context up to `T_max` in Phase 6 for simplicity, with the ring
buffer as a documented optimisation for Phase 8. This costs 28 MiB and removes an entire class of
position-tracking bugs from the first implementation.

### 4.2 Transient buffers

The dominant transient is the **attention score matrix**. With a sliding window of `W` over `T`
positions, a straightforward prefill implementation allocates `H × W × T` scores; a full-attention one
allocates `H × T × T`.

| `T` | Windowed (`H·W·T`, `binary32`) | Full (`H·T·T`, `binary32`) | Ratio |
| --- | --- | --- | --- |
| 256 | 2.00 MiB | 2.00 MiB | 1.0× |
| 512 | 4.00 MiB | 8.00 MiB | 2.0× |
| 1024 | 8.00 MiB | 32.00 MiB | 4.0× |
| 2048 | **16.00 MiB** | 128.00 MiB | 8.0× |
| 4096 | 32.00 MiB | 512.00 MiB | 16.0× |

At `T = 4096` full attention needs 512 MiB for a single layer's scores — **exactly the entire runtime
working target**, for one temporary allocation. This is the clearest single argument for the window,
and it is a memory argument, not a compute one.

Other transients (Config M, `T = 2048`, `binary32`):

| Buffer | Formula | Size |
| --- | --- | --- |
| MLP inner activation | `T · d_ff · bpp` | 5.38 MiB |
| Activations (hidden states) | `T · d · bpp` | 2.00 MiB |
| Logits row (one position) | `V · bpp` | 32.00 KiB |
| RMSNorm scratch | `T · bpp` per norm | 8.00 KiB |

### 4.3 Runtime overhead

| Item | Budget | Basis |
| --- | --- | --- |
| Allocator metadata | 2 MiB | Assumption, generous |
| Code and read-only data | 1 MiB | Assumption for a small C binary |
| Stack (main thread) | 8 MiB | Typical default; configurable |
| Tokenizer working set | 1 MiB | Input buffer plus indices |
| **Total overhead** | **≤ 12 MiB** | Sum |

### 4.4 Total runtime residency — Config M

Using full-context KV cache at `T_max = 2048` and a windowed score buffer (worst case across the
table):

| Component | Size |
| --- | --- |
| Weights (`binary32`) | 32.14 MiB |
| KV cache (full context, 2048) | 32.00 MiB |
| Score buffer (windowed) | 16.00 MiB |
| MLP activation | 8.00 MiB |
| Activations | 2.00 MiB |
| Logits row | 0.03 MiB |
| Runtime overhead | 12.00 MiB |
| **Total** | **≈ 99.55 MiB** |

That is **4.86 % of the 2 GiB address-space budget** and **19.4 % of the 512 MiB working target**.

With int8 weight storage (§[`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §4), weights drop to
8.04 MiB and the total to **≈ 75.44 MiB**.

---

## 5. Budget 3 — Peak inference memory, across configurations

| Config | Weights | KV (full) | Scores (win.) | Other | Overhead | **Peak** | % of 2 GiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Config N (`T_max=512`, `W=128`, `d=128`) | 7.02 MiB | 2.00 MiB | 1.00 MiB | 1.00 MiB | 12.00 MiB | **22.97 MiB** | 1.12 % |
| Config M (`T_max=2048`, `W=256`, `d=256`) | 32.14 MiB | 32.00 MiB | 16.00 MiB | 7.41 MiB | 12.00 MiB | **99.55 MiB** | 4.86 % |

Both configurations fit the budget with two orders of magnitude of headroom on the headline figure.

**This is not a compatibility claim.** It is an arithmetic statement about a design. Whether the
resulting binary actually allocates these amounts, and whether the 32-bit process runs, is Phase 7's
question. A design that fits on paper can still exceed an allocation limit because of fragmentation,
allocator behaviour, or a bug.

### 5.1 Peak inference vs context length (Config M)

Illustrating where the model stops being comfortable if the window is abandoned:

| Context | Windowed total | Full-attention total |
| --- | --- | --- |
| 512 | ≈ 58.0 MiB | ≈ 62.0 MiB |
| 1024 | ≈ 71.9 MiB | ≈ 95.9 MiB |
| 2048 | **≈ 99.5 MiB** | **≈ 211.5 MiB** |
| 4096 | ≈ 154.9 MiB | **≈ 634.9 MiB** |
| 8192 | ≈ 265.7 MiB | ≈ 2249.7 MiB — **exceeds the 2 GiB budget** |

The last row is the concrete failure mode this architecture exists to avoid: full attention at 8 K
context does not fit a 32-bit process. The windowed design does.

---

## 6. Budget 4 — Training memory

### 6.1 Fixed cost

AdamW `[S20]` keeps two moment estimates per parameter. With `binary32` throughout:

| Item | Bytes/parameter | Config M (8 425 728 params) | Config N (1 840 256 params) |
| --- | --- | --- | --- |
| Weights | 4 | 32.14 MiB | 7.02 MiB |
| Gradients | 4 | 32.14 MiB | 7.02 MiB |
| Adam first moment | 4 | 32.14 MiB | 7.02 MiB |
| Adam second moment | 4 | 32.14 MiB | 7.02 MiB |
| **Fixed total** | **16** | **128.57 MiB** | **28.08 MiB** |

The fixed cost alone is 6.25 % of the address-space budget for Config M — acceptable.

### 6.2 Activation cost, and why checkpointing is mandatory

Activation storage for the backward pass dominates. Estimating per sample per layer as
`(8·T·d + 2·H·T² + 2·T·d_ff) · bpp` in `binary32`:

**Config M, `T = 512`:**

| Micro-batch | Activations | Total training memory |
| --- | --- | --- |
| 1 | 181.50 MiB | **310.07 MiB** |
| 2 | 363.00 MiB | 491.57 MiB |
| 4 | 726.00 MiB | 854.57 MiB |
| 8 | 1452.00 MiB | **1580.57 MiB** |
| 16 | 2904.00 MiB | **3032.57 MiB — exceeds the 2 GiB budget** |

At a micro-batch of 8, training consumes 1 580.57 MiB — 77 % of the budget, with no room for the OS,
fragmentation, or a larger vocabulary. At 16 it is impossible.

**With activation checkpointing** (store one layer's activations, recompute the rest during backward):

| Micro-batch | Activations | Total |
| --- | --- | --- |
| 1 | 22.69 MiB | 151.25 MiB |
| 2 | 45.38 MiB | 173.94 MiB |
| 4 | 90.75 MiB | **219.32 MiB** |
| 8 | 181.50 MiB | **310.07 MiB** |
| 16 | 363.00 MiB | 491.57 MiB |

**Config N, `T = 256`:**

| Micro-batch | Activations | Total |
| --- | --- | --- |
| 4 | 58.75 MiB | **86.83 MiB** |
| 8 | 117.50 MiB | **145.58 MiB** |
| 16 | 235.00 MiB | 263.08 MiB |
| 32 | 470.00 MiB | 498.08 MiB |

### 6.3 Consequences for Phase 5

These figures produce four requirements that are design requirements, not optimisations:

1. **Activation checkpointing is mandatory** from the first training implementation. Without it,
   Config M needs 1 580.57 MiB at micro-batch 8 and 3 032.57 MiB at 16 — the latter exceeds the budget
   outright.
2. **Config N is trainable without checkpointing** at micro-batch 8 (145.58 MiB), which is another
   reason it comes first.
3. **Gradient accumulation is mandatory** to reach a useful effective batch from micro-batches of 2–8.
4. **Optimiser state could be narrowed** to `binary32` weights with `bfloat16`-stored moments later,
   but this is a Phase 8 optimisation and would need measured quality evidence first.

**[OPEN]** Whether checkpointed training reaches the same optimum as un-checkpointed training at
matched effective batch is an empirical question. Checkpointing changes floating-point reduction order,
so exact equality is not expected; tolerance is defined in
[`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §5.

### 6.4 Training does not fit a 512 MiB working target

Worth stating explicitly: **inference fits 512 MiB; training does not** for Config M (219.32 MiB at
micro-batch 4 checkpointed is within 512 MiB, but the working-headroom margin is thin). The working
target in §2.1 applies to the **runtime**. Training is a development workflow, not a deployment
scenario, and is budgeted against 2 GiB directly. Config N training (145.58 MiB) does fit inside 512 MiB.

---

## 7. Fragmentation and safety headroom

An address space is not a heap. A design that fits in total bytes can still fail to allocate because
no contiguous region is large enough.

| Concern | Mitigation |
| --- | --- |
| Large contiguous allocation fails despite total free VA | Allocate all major buffers **once**, at start-up, in a single arena; never free and reallocate large blocks during inference |
| Allocator metadata growth | Arena allocator with no per-allocation overhead in steady state |
| Fragmentation over long uptime | No dynamic allocation in the decode loop; the model is loaded once and runs to completion |
| Mapped model file consumes VA | Documented: `mmap` counts against the 2 GiB; a file-backed model at 32 MiB is accounted in §4.4 |
| Stack exhaustion via recursion | No recursion over input-dependent depth ([`SECURITY_MODEL.md`](SECURITY_MODEL.md) §6) |
| Silent overcommit | Runtime checks actual allocation success and fails explicitly ([`SECURITY_MODEL.md`](SECURITY_MODEL.md) §7) |

**[PROPOSED]** A single pre-allocated arena, sized from the model's declared metadata and validated
against a configured maximum before the first byte is read
([`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §6).

---

## 8. Summary of budgets

| Budget | Config T | Config N | Config M | Status |
| --- | --- | --- | --- | --- |
| **1. Model storage** | ≤ 2.47 MiB | ≤ 8.62 MiB | ≤ 33.74 MiB | Derived |
| **2. Runtime residency** | ≤ 13.61 MiB | ≤ 22.97 MiB | ≤ 99.55 MiB | Derived |
| **3. Peak inference** | ≤ 13.61 MiB | ≤ 22.97 MiB | ≤ 99.55 MiB | Derived |
| **4. Training (checkpointed)** | ≤ 4.15 MiB | ≤ 145.58 MiB | ≤ 310.07 MiB | Derived |
| Inference vs 2 GiB budget | 0.66 % | 1.12 % | 4.86 % | Derived |
| Inference vs 512 MiB target | 2.6 % | 4.5 % | 19.4 % | Derived |

Config T ([`ARCHITECTURE_SPEC.md`](ARCHITECTURE_SPEC.md) §5.4) is a pipeline-validation fixture, not a
target configuration. It is listed because it is the one configuration that can be **trained inside the
32-bit envelope itself** (4.15 MiB checkpointed), which makes it the vehicle for the first end-to-end
32-bit test — mechanics only, no capability claim.

All four budgets fit the stated envelope with substantial headroom.

**What this does not establish:** that AETHER runs on any 32-bit system. It establishes that the
*paper design* fits the *paper budget*. Those are different claims, and only the second is being made
here.

---

## 9. Unresolved questions

1. Is the 2 GiB conservative budget correct for the real target population? **[OPEN]** — Phase 7.
2. Does a 32-bit allocator actually satisfy the single-arena strategy at these sizes? **[OPEN]**
3. Is the activation estimate in §6.2 accurate once real kernels exist? It is a formula-based estimate
   and could be wrong in either direction. **[OPEN]**
4. Does ring-buffer KV (4 MiB) behave identically to full-context KV (32 MiB) for windowed attention?
   Mathematically it should, but boundary handling at the ring wrap is a classic bug source. **[OPEN]**
5. What is the real fragmentation behaviour over a multi-hour training run? **[OPEN]**
