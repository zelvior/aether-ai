# AETHER — Platform Compatibility Plan

Status: **Empty of results by design.** This document defines *how* AETHER will earn a compatibility
claim, and records that **no claim has been earned**. There is no 32-bit build, no test matrix, and no
measurement.

Related: [`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) (the hardware reality) ·
[`RUNTIME_SPEC.md`](RUNTIME_SPEC.md) (what would be built) · [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md)
(the envelope) · [`ROADMAP.md`](ROADMAP.md) Phase 7

---

## 1. The rule this document enforces

> **A compatibility claim requires a build that ran and a test that passed, and the claim must state
> the exact configuration in which that happened.**

No exceptions. Not "the code is portable", not "it should work", not "our design avoids 64-bit types".
Those are hypotheses. `RESEARCH_PRINCIPLES.md` already commits the project to this; this document is
the mechanism.

### 1.1 Current state of every claim

| Claim | Status |
| --- | --- |
| Builds on 32-bit x86 | **NOT CLAIMED** |
| Runs on 32-bit x86 | **NOT CLAIMED** |
| Fits in 2 GiB address space | **NOT CLAIMED** (arithmetic suggests it would; nothing has been loaded) |
| Works on Windows | **NOT CLAIMED** |
| Works on Linux | **NOT CLAIMED** |
| Tested on any hardware | **NOT CLAIMED** |

---

## 2. The claim ladder

Each rung is a strictly stronger statement. **No rung may be skipped**, and rung `n` may only be
claimed when rung `n−1` has been demonstrated on the same configuration.

| # | Claim | Requires | Evidence artefact |
| --- | --- | --- | --- |
| **L0** | *Design intent* | Arithmetic in `MEMORY_BUDGET.md` | This document. **Not a compatibility claim.** |
| **L1** | *Compiles* | A 32-bit build in CI, producing a binary | CI log + binary checksum |
| **L2** | *Loads a model* | Runtime parses a real `.aether` file and reports metadata | Dump of parsed tensor metadata |
| **L3** | *Produces output* | Forward pass on fixed input, deterministic output | Output tensor checksum |
| **L4** | *Matches 64-bit* | Equivalence within stated tolerance | Equivalence report per `EVALUATION_PLAN.md` §5 |
| **L5** | *Fits the budget* | Measured peak RSS and peak virtual size, reported | Measurement table |
| **L6** | *Sustains use* | Multi-turn session without growth, leak-free | Soak-test log |

**AETHER is at L0.** That is the honest position and this table exists so it cannot be overstated.

---

## 3. The configuration matrix

A claim is meaningless without stating what it was tested on. Every rung above must be reported
against a full coordinate:

| Dimension | Values to cover |
| --- | --- |
| **Pointer width** | 32-bit (required), 64-bit (reference) |
| **Architecture** | i686 with x87 only; i686 with SSE2 *(two different targets)* |
| **OS** | Linux, Windows *(separately — §7 of `CPU_32BIT_RESEARCH.md`)* |
| **Compiler** | At least two independent toolchains |
| **Optimisation** | `-O0`, `-O2`, and the shipping level |
| **Build type** | With and without assertions |

That is `2 × 2 × 2 × 2 × 3 × 2` = **96 cells** at full coverage. That is not achievable and not
intended: AETHER will claim only the cells it actually runs, and state the rest as **untested**.

### 3.1 The minimum defensible matrix

**[PROPOSED]** The smallest matrix worth publishing:

| Cell | Pointer | ISA | OS | Compiler | Build |
| --- | --- | --- | --- | --- | --- |
| R1 | 64-bit | x86-64 | Linux | GCC | `-O2` |
| R2 | 32-bit | i686 + SSE2 | Linux | GCC | `-O2` |
| R3 | 32-bit | i686, x87 only | Linux | GCC | `-O2` |
| R4 | 32-bit | i686 + SSE2 | Linux | Clang | `-O2` |
| R5 | 32-bit | i686 + SSE2 | Windows | MSVC | release |

**R3 is the critical cell** and the one most likely to fail: it forces the x87 fallback path and the
no-SSE2 path simultaneously. A project that only tests R2 has not tested its portability claim.

---

## 4. What counts as a failure

A build that runs but produces different output is a **failure**, not a caveat. The tolerance in
`EVALUATION_PLAN.md` §5 — ≤ 1e-3 relative, ≥ 99 % greedy token agreement — exists because bit-exactness
across x87 and SSE2 is not achievable, and pretending otherwise would produce a test that can only
fail. But:

| Observation | Verdict |
| --- | --- |
| Output differs by > 1e-3 relative **(same precision)** | **Failure** |
| Greedy agreement < 99 % | **Failure** |
| Bit-exact equality | **Suspicious** — investigate, likely both paths used the same code |
| Peak RSS exceeds the declared budget | **Failure** |
| Any crash, any sanitizer finding | **Failure** |
| Runs only with assertions disabled | **Failure** |

The third row matters: a 32-bit build that is bit-identical to the 64-bit build has probably not
exercised a different code path at all, and the "pass" would be vacuous.

**The 1e-3 rule applies only to comparisons at equal precision.** `NUMERICAL_STRATEGY.md` §9A shows that
an int8-quantised model differs from its `binary32` reference by ≈ 2 × 10⁻² — twenty times the failure
threshold — while behaving correctly. Phase 8 therefore needs a **separate, separately derived
tolerance**, and applying this table unchanged to a quantised model would reject a working build.

---

## 5. How the environment gets created

Phase 7 requires a real environment. Options, all unresolved:

| Approach | Advantage | Disadvantage |
| --- | --- | --- |
| Native 32-bit hardware | Truest signal | Hard to obtain, slow, hard to automate |
| 32-bit VM | Real 32-bit kernel and address space | Needs a 32-bit OS image; slower |
| 32-bit container / userland | Easy in CI | Shares the 64-bit kernel; **not a true address-space test** |
| Cross-compile + `qemu-i386` | Easy, tests codegen | Emulated FPU may differ from real x87 |
| Cross-compile + real 32-bit CPU in CI | Best available | Infrastructure |

**The third row is a trap.** A 32-bit userland on a 64-bit kernel can allocate above 4 GiB via
`mmap`, so it will *not* detect a 32-bit address-space failure — precisely the failure Phase 7 exists
to find. AETHER must not accept a container-based "32-bit pass" as evidence for L5.

**[OPEN]** Which approach is feasible is unresolved and depends on available infrastructure.
[`ROADMAP.md`](ROADMAP.md) Phase 7 states the phase cannot begin until such an environment exists.

---

## 6. CI policy

The Phase 1 workflow deliberately does **not** attempt 32-bit builds
(`.github/workflows/repository-checks.yml`), and `ROADMAP.md` Phase 7 states that automated CI is
added only once the environment exists.

That policy stands and this document does not weaken it:

| Do | Do not |
| --- | --- |
| Add a 32-bit job once R2/R3 can run | Add a job that cross-compiles and calls it "tested" |
| Publish the matrix with gaps marked | Publish a green badge implying full coverage |
| Record the toolchain version per cell | Claim a compiler version was tested when it was not |

---

## 7. Degradation behaviour to be specified

When memory is insufficient, AETHER must fail clearly rather than thrash. Specified as a requirement
here; implemented in Phase 6:

| Condition | Required behaviour |
| --- | --- |
| Model exceeds declared budget | Refuse to load, state the requirement and the available amount |
| Allocation fails mid-inference | Terminate the request; do not partially degrade silently |
| Context would exceed buffer | Truncate deterministically and **report** truncation |
| Address space exhausted | Exit non-zero with an error, not a swap-induced hang |

The last row is the one a 32-bit machine will actually hit, and "hang for ten minutes then die" is a
worse outcome than "refuse immediately".

---

## 8. What this document is not

- It is **not** a support statement.
- It is **not** a compatibility matrix — §3.1 is a *plan* for one.
- It is **not** evidence of portability. Portability is a property of code that has been compiled and
  run in more than one configuration, and no such code exists.

---

## 9. Unresolved questions

1. Which of §5's five approaches is available? **Blocks Phase 7 entirely.** **[OPEN]**
2. Is a second toolchain (R4) worth the CI cost in the first iteration? **Proposed: yes — one toolchain
   tests code, two test the *language*.** **[OPEN]**
3. Can a 32-bit Windows cell be automated at all, or must it be manual and periodic? **[OPEN]**
4. Should L5 (fits the budget) be a CI gate or a published measurement? **Proposed: published
   measurement — CI runners are not representative machines.** **[OPEN]**
5. What is the declared peak-RSS budget per configuration, given `MEMORY_BUDGET.md` gives arithmetic
   rather than measurement? **Proposed: arithmetic + 25 % headroom.** **[OPEN]**

---

## 10. Status summary

| Item | Status |
| --- | --- |
| Claim ladder | **Defined** (§2) |
| Current rung | **L0 — design intent only** |
| Configuration matrix | **Planned**, not run |
| Minimum defensible matrix | **Proposed** (5 cells) |
| CI 32-bit job | **Does not exist, and must not exist until it can be real** |
| Any build, test, or measurement | **None.** |
