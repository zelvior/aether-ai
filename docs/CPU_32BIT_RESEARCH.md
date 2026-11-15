# AETHER — Native 32-bit x86 Research

Status: **Research and proposal.** No 32-bit build exists. **This document makes no compatibility claim.**
Nothing here has been executed on real 32-bit hardware.

Related: [`PLATFORM_COMPATIBILITY_PLAN.md`](PLATFORM_COMPATIBILITY_PLAN.md) (how claims will be earned) ·
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) (the envelope) · [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md)
(x87 and SIMD) · [`RUNTIME_SPEC.md`](RUNTIME_SPEC.md) (execution)

---

## 1. What "32-bit x86" actually means

The phrase collapses several independent constraints, and conflating them causes bad decisions:

| Constraint | What it determines | Independent of |
| --- | --- | --- |
| **Pointer width (32 bit)** | Addressable memory ceiling; `sizeof(void*) == 4` | Instruction set |
| **Instruction set (i386 / i686)** | Available registers and SIMD | Width |
| **FPU model (x87)** | Floating-point precision behaviour | Width, and usually co-occurs |
| **Address-space limit (2–3 GiB)** | Practical process ceiling | Physical RAM |
| **OS and toolchain** | What can be built and run at all | All of the above |

A 32-bit process can run on a 64-bit CPU; a 64-bit process cannot run on a 32-bit CPU. A 32-bit build
with SSE2 available is a different target from one without. **AETHER targets the intersection**, which
is the i386/i686 baseline with x87 and no assumed SSE2.

---

## 2. Address space: theoretical vs practical

This distinction is the most consequential in the entire document.

### 2.1 The theoretical ceiling

A 32-bit pointer addresses `2³²` = 4 GiB. That number appears in specifications and is **never
achievable by a normal process.**

### 2.2 The practical ceiling

| Limit | 32-bit Linux | 32-bit Windows |
| --- | --- | --- |
| Total virtual address space | 4 GiB | 4 GiB |
| Kernel/user split | Typically **3 GiB user** | Typically **2 GiB user** |
| With large-address-aware / `3G` boot option | n/a | **3 GiB user** (executable must opt in) |
| Contiguous allocation ceiling | Fragmentation limits the largest free block, not the total | Same, and worse in practice |
| Guard pages, thread stacks, libraries | Consume part of the user space | Same |

**AETHER plans against 2 GiB, not 3 GiB and certainly not 4 GiB**, because:

1. 2 GiB is the default user-mode limit on 32-bit Windows, and
2. a design that fits 2 GiB fits 3 GiB, but not the reverse.

[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2 uses 2 GiB as the design envelope and 512 MiB as the
*working target* — deliberately far below the ceiling.

### 2.3 Why the working target is 512 MiB and not 1.5 GiB

Fitting is not the same as running well:

- **Fragmentation.** Long-lived allocations (weights) plus short-lived (activations) plus model
  loading creates a fragmented heap; the largest contiguous block shrinks over time.
- **Page-file dependence.** A process near its address-space ceiling depends on swap for normal
  behaviour, which converts an out-of-memory condition into thrashing.
- **Other software.** A user's machine is not dedicated.
- **Measurement honesty.** A model that "fits in 1.5 GiB" is a model that works only on an idle
  machine with a large page file. That is not a property worth claiming.

**512 MiB is the target because it leaves room for the operating system to misbehave**, which it will.

---

## 3. The FPU: x87 is the baseline, and it is not IEEE-clean

32-bit x86 floating point defaults to the **x87 FPU**, which computes in 80-bit extended precision
internally. This has a direct consequence: the value of an expression can depend on whether the
compiler kept an intermediate in a register or spilled it to memory.

Full treatment in [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §2. The decisions that follow:

| Decision | Reason |
| --- | --- |
| `binary32` storage only | `float` and `double` are both representable; extended is not storable portably |
| Documented reduction order | Register/spill behaviour must not change results |
| `-ffloat-store` / `-fexcess-precision=standard` required | Forces round-to-`binary32` at statement boundaries |
| SSE2 **not** assumed | i386 baseline predates it; a fallback path is mandatory |
| No `long double` in the format | x87 extended does not exist on non-x86 targets |

**[ESTABLISHED]** the x87 behaviour is a property of the architecture.
**[PROPOSED]** the mitigations; their sufficiency is unmeasured until a build exists.

---

## 4. SIMD availability, and why SSE2 cannot be assumed

| Extension | Year | Baseline? | AETHER use |
| --- | --- | --- | --- |
| x87 | 1985 | Yes | Scalar fallback |
| MMX | 1996 | No | Not used |
| SSE | 1999 | No | Optional |
| **SSE2** | 2001 | **No, not on i386** | Optional fast path |
| SSE3+ | 2004+ | No | Not used |
| AVX / AVX2 | 2011+ | No, 64-bit only | Out of scope |

**SSE2 is guaranteed on x86-64 but is a *runtime feature* on i386.** A 1999-vintage Pentium III has
SSE but not SSE2; a 2001 Pentium 4 has SSE2. Since "native 32-bit x86" includes machines from both
eras, AETHER's portable baseline is **x87 scalar**, with SIMD as an optional runtime-selected path.

### 4.1 Runtime dispatch, not compile-time

```c
/* illustrative only — no implementation exists */
int has_sse2 = cpu_has_sse2();           /* CPUID, cached once */
if (has_sse2) sse2_matmul(...); else x87_matmul(...);
```

**[PROPOSED]** Compile-time `-msse2` globally is **rejected**: it produces a binary that faults on
exactly the machines the project claims to serve.

### 4.2 Register pressure is the real constraint

i386 has **8 general-purpose registers** and, without SSE, **8 x87 stack registers** used as a stack.
x86-64 has 16 GPRs and 16 SSE registers. For the inner loop of a matmul, this is the difference
between keeping three pointers and two accumulators in registers (i386, leaving little) and doing the
same comfortably (x86-64).

**Practical consequence:** on i386 the kernel will spill. That is expected and is one of the reasons
`TRAINING_FEASIBILITY.md` §3.3's throughput priors are given as ranges, not numbers.

---

## 5. Memory model and allocation

| Concern | 32-bit consequence |
| --- | --- |
| `size_t` is 32-bit | Every `size` computation can overflow at 4 GiB; `SIZE_MAX` is 4,294,967,295 |
| `ptrdiff_t` is 32-bit signed | Difference of two pointers beyond 2 GiB is UB |
| Allocation overhead | Per-allocation headers (typically 8–16 bytes) matter at thousands of small allocations |
| Alignment | `malloc` may return 8-byte alignment; 16-byte requires `posix_memalign` / `_aligned_malloc` |
| Large allocations | A single `malloc` of hundreds of MiB depends on contiguity |

### 5.1 The overflow discipline

**Every** arithmetic operation on a size, offset, or tensor dimension must be checked before it is used
to allocate. [`MODEL_FORMAT_SPEC.md`](MODEL_FORMAT_SPEC.md) §7 specifies the validation sequence; the
rule this document contributes is:

> On a 32-bit target, `a * b > SIZE_MAX` is a **reachable** condition, not a theoretical one. A model
> file is untrusted input. Every multiply is checked.

A concrete example computed from AETHER's own dimensions, using the *full* (non-windowed) attention
score buffer at `T_max = 8192`, `H = 8`, `b = 8`, `binary32`:

```
b × H × T × T × 4  =  8 × 8 × 8192 × 8192 × 4  =  17,179,869,184 bytes
```

That exceeds `2³²` by a factor of four, and — this is the important part — **wraps to exactly zero**
in `uint32_t` arithmetic:

```
17,179,869,184  mod  2³²  =  0
```

An unchecked `size_t` multiply therefore yields a **zero-byte allocation that succeeds**. The buffer
appears valid, and the first write runs off the end of it. This is not a hypothetical: it is what
AETHER's own Config M dimensions produce at its own maximum context, with a batch size of 8, on a
32-bit target.

The discipline that follows:

1. Compute every byte count in a type wide enough to **detect** the failure (`uint64_t`).
2. Compare against `SIZE_MAX` and against a declared per-buffer ceiling.
3. Only then narrow to `size_t`.
4. Never compute a size and immediately allocate it.

Note also that at `T = 8192` a *full* attention buffer would be 16 GiB before any overflow
consideration, so the correct fix is architectural, not arithmetic: this is precisely why Config M is
specified with a **sliding window** (`ARCHITECTURE_SPEC.md` §4.2) and why
[`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §5 shows full attention exceeding 2 GiB at context 8192.

---

## 6. Compiler and toolchain considerations

| Question | Status |
| --- | --- |
| Does GCC support `-m32`? | Yes, where 32-bit multilib libraries are installed |
| Does Clang? | Yes, with a 32-bit sysroot |
| Does MSVC? | Yes, via the 32-bit toolset |
| Is a 32-bit Rust target available? | `i686-unknown-linux-gnu`, `i686-pc-windows-msvc` are tier-1/2 targets |
| Has AETHER built anything for any of these? | **No.** |

[`PLATFORM_COMPATIBILITY_PLAN.md`](PLATFORM_COMPATIBILITY_PLAN.md) defines how each of these becomes a
verified rather than assumed statement. **No toolchain claim in this document is a compatibility
claim.** "Supports `-m32`" describes the compiler, not AETHER.

### 6.1 Language choice is unresolved

C, C99, C11 and Rust are all plausible. AETHER does **not** decide in Phase 2, because the decision
depends on which toolchains actually produce working 32-bit binaries in the Phase 7 environment, and
that environment does not exist yet.

| Language | Argument for | Argument against |
| --- | --- | --- |
| C99 | Universal 32-bit support; predictable codegen; smallest runtime | Manual memory safety |
| Rust | Memory safety; `no_std` possible | 32-bit target support varies; panics need handling |
| C++ | Familiar; tooling | Runtime size; exceptions on 32-bit are a liability |

**[OPEN]** — maintainer decision, deliberately deferred.

---

## 7. Operating system differences

| Aspect | Linux (i386) | Windows (32-bit) |
| --- | --- | --- |
| User address space | Typically 3 GiB | **2 GiB** default (`/LARGEADDRESSAWARE` → 3 GiB) |
| Memory mapping | `mmap` | `CreateFileMapping` / `MapViewOfFile` |
| Alignment primitive | `posix_memalign` | `_aligned_malloc` |
| File I/O | `read` / `pread` | `ReadFile` |
| Strict aliasing | Compiler-dependent | Compiler-dependent |
| Threads | `pthreads` | Win32 threads |
| Long paths | — | `MAX_PATH` limitations |

**AETHER's portable layer must abstract exactly these**, and nothing more. Every abstraction added
here is a place where 32-bit behaviour can diverge, and `EVALUATION_PLAN.md` §5's equivalence testing
exists to catch that divergence.

---

## 8. A practical minimum hardware profile — a proposal, not a guarantee

**[PROPOSED]** AETHER's declared minimum profile for 32-bit execution:

| Component | Minimum | Rationale |
| --- | --- | --- |
| CPU | i686-class, x87 FPU | Portable baseline; no SSE2 requirement |
| RAM | 256 MiB | Config T peak is 13.61 MiB; leaves room for the OS |
| Free disk | 30 MiB | Config N full-precision storage is ≤ 8.62 MiB |
| OS | Any supported 32-bit OS with a conforming libc | — |
| Address space | 2 GiB user-mode | Config T and N fit with large headroom |

**This is a research proposal derived from arithmetic, not a tested configuration.** It will be revised
by Phase 7 measurements, and until then no user should treat it as a support statement.

### 8.1 What the profile implies about ambition

Config M's peak inference of 99.55 MiB ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §5) fits comfortably in
256 MiB. Config T's 13.61 MiB leaves enormous headroom. **The memory arithmetic is not the hard part
of this project** — [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §4 and
[`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5.1 are.

---

## 9. Common claims that must not be made

| Tempting claim | Why it is forbidden |
| --- | --- |
| "Runs on 32-bit x86" | No build exists |
| "Fits in 2 GiB" | Arithmetic says yes; nothing has been loaded |
| "Works on Windows 98" | Not tested; toolchain and libc assumptions unverified |
| "No 64-bit assumptions" | Nothing has been compiled, so nothing has been checked |
| "Compatible with `<CPU>`" | No compatibility matrix exists |
| "SIMD-accelerated" | No kernel exists |

Every one of these describes a **plan**. [`PLATFORM_COMPATIBILITY_PLAN.md`](PLATFORM_COMPATIBILITY_PLAN.md)
is the document that converts plans into claims, and it is currently empty of results by design.

---

## 10. Unresolved questions

1. Which compiler/target actually produces a working 32-bit build of anything in this project? **Unknown.** **[OPEN]**
2. Is `-ffloat-store` sufficient to make x87 match SSE2 numerically, and what does it cost in
   throughput? **[OPEN]**
3. Does the runtime need `mmap`-based weight loading to avoid a large contiguous `malloc`? **[OPEN]**
4. What is the largest single contiguous allocation a 32-bit process can realistically obtain on the
   target OS? **Unmeasured.** **[OPEN]**
5. Is 256 MiB RAM the right floor, or should the declared minimum be 128 MiB? **[OPEN]**
6. Does Rust's 32-bit target support meet AETHER's needs, or does that force C? **Maintainer decision.** **[OPEN]**

---

## 11. Status summary

| Item | Status |
| --- | --- |
| 2 GiB design envelope | **Derived** from Windows default; conservative |
| 512 MiB working target | **Proposed** — deliberately far below ceiling |
| x87 as baseline FPU | **Established** architecture fact; mitigations proposed |
| SSE2 not assumed | **Established** — correct for i386 |
| Runtime CPU dispatch required | **Proposed**, and non-negotiable given the above |
| Overflow-safe size arithmetic | **Required**; specified in `MODEL_FORMAT_SPEC.md` §7 |
| Minimum hardware profile | **Proposed**, derived from memory arithmetic |
| Any 32-bit build or test | **None.** |
| Any compatibility claim | **None, and none may be made.** |
