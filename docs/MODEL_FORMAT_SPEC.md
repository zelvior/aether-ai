# AETHER — Model Format Specification

Format name: **AETHER Model Container (AMC)**
Format version: **1** (proposed)

Status: **Proposal.** Nothing implements this format. No file conforming to it exists.

This specification is written to be implementable in dependency-free C and to be **parsable safely
from untrusted input**. Safety requirements come from [`SECURITY_MODEL.md`](SECURITY_MODEL.md) §3–4;
this document turns them into a byte layout and a validation sequence.

---

## 1. Design rules

| # | Rule | Reason |
| --- | --- | --- |
| F1 | **Data only.** No executable content, no callables, no serialisation that can run code | [`SECURITY_MODEL.md`](SECURITY_MODEL.md) §3 |
| F2 | **Validate before allocate.** Every size checked against limits and for overflow *before* any allocation | Prevents hostile allocation |
| F3 | **Self-describing.** The parser learns tensor count, shapes, and dtypes from the file; it does not assume a layout | Allows architecture evolution without a new parser |
| F4 | **Little-endian, fixed field widths.** Explicit byte order in the spec, not the host's | Portability across targets |
| F5 | **Versioned with an explicit incompatible boundary.** Unknown major version → reject; unknown minor features → skip by length | Forward compatibility |
| F6 | **Bounded.** Hard limits on every count and size, enforced before use | DoS resistance |
| F7 | **Trivially streamable.** A loader can read the header, decide, then stream tensors without seeking | Works for both `mmap` and sequential reads |
| F8 | **No pickle, ever.** Structurally impossible: the format has no mechanism for arbitrary objects | Removes the entire class |

---

## 2. Endianness and alignment

- **All multi-byte integers and floats are little-endian.** On a big-endian host the loader must
  byte-swap; AETHER does not currently target big-endian, and the loader **rejects** with a clear
  error if it cannot honour the order.
- **Headers are 4-byte aligned.** Tensor *data* begins at a 64-byte-aligned offset, so that a vector
  kernel may assume 64-byte alignment for a row start without unaligned-load penalties.
- **No padding between header records**; padding only to satisfy the alignment rule above, and it is
  all zeros.

---

## 3. File layout

```
┌──────────────────────────────────────────────────────────────┐  0
│  Header (fixed, 256 bytes)                                   │
├──────────────────────────────────────────────────────────────┤ 256
│  Architecture Metadata Block (AMB) — length-prefixed          │
├──────────────────────────────────────────────────────────────┤
│  Tensor Table (TT) — length-prefixed, N entries × 64 bytes    │
├──────────────────────────────────────────────────────────────┤
│  Tokenizer Block (TB) — length-prefixed                       │
├──────────────────────────────────────────────────────────────┤
│  Integrity Block (IB) — length-prefixed                       │
├──────────────────────────────────────────────────────────────┤  ← 64-byte aligned
│  Tensor Data Region                                          │
│    tensor 0                                                  │
│    tensor 1   (each starting 64-byte aligned)                │
│    …                                                         │
└──────────────────────────────────────────────────────────────┘
```

The Tensor Data Region begins at the first 64-byte boundary at or after the end of the Integrity
Block. **No field anywhere may point backwards into the header region.**

---

## 4. Header (256 bytes, offset 0)

| Offset | Size | Field | Type | Meaning |
| --- | --- | --- | --- | --- |
| 0 | 8 | `magic` | bytes | `41 45 54 48 45 52 00` + `01`? — see §4.1 |
| 8 | 4 | `format_version` | `u32` | Must be `1` for this spec |
| 12 | 4 | `header_size` | `u32` | Must be `256` |
| 16 | 4 | `flags` | `u32` | Bit 0: tensor data is int8-quantised (v1: must be 0) |
| 20 | 4 | `amb_size` | `u32` | Architecture Metadata Block length, bytes |
| 24 | 4 | `tensor_count` | `u32` | Number of entries in the Tensor Table, `1 … 4096` |
| 28 | 4 | `tt_size` | `u32` | Tensor Table length; must equal `tensor_count × 64` |
| 32 | 4 | `tb_size` | `u32` | Tokenizer Block length, bytes |
| 36 | 4 | `ib_size` | `u32` | Integrity Block length, bytes |
| 40 | 4 | `data_region_offset` | `u32` | Absolute file offset of the Tensor Data Region |
| 44 | 4 | `reserved0` | `u32` | Must be `0` |
| 48 | 8 | `file_size` | `u64` | Total file length, bytes; must match actual |
| 56 | 8 | `data_region_size` | `u64` | Total bytes of tensor data |
| 64 | 8 | `param_count` | `u64` | Declared total parameters (informational, validated) |
| 72 | 8 | `data_checksum` | `u64` | FNV-1a 64 over the Tensor Data Region |
| 80 | 32 | `format_uuid` | bytes | Records the exact format revision |
| 112 | 32 | `reserved1` | bytes | Must be all zeros |
| 144 | 112 | `reserved2` | bytes | Must be all zeros — room for v1.x additions without moving sections |

Total: 256 bytes.

**[PROPOSED]** Reserving 144 bytes of zero space in the header allows adding fields in a minor version
without relocating anything, at the cost of a slightly larger file. A parser in v1 rejects a header
whose reserved bytes are non-zero, which is how a v1 parser refuses to misinterpret a v1.x file.

### 4.1 Magic

The first 8 bytes are the ASCII string `AETHER` followed by two NUL bytes, then the version bytes:

```
offset 0: 'A' 'E' 'T' 'H' 'E' 'R' 0x00 0x00
offset 8: format_version (u32 LE) = 1
```

Rationale: the magic is human-recognisable in a hex dump (useful for debugging, and for a user to
identify a stray file), and contains no byte sequence that would be interpreted as a text encoding
marker or shell escape.

---

## 5. Architecture Metadata Block (AMB)

A sequence of records, each length-prefixed, so an unknown record can be skipped:

| Offset | Size | Field | Meaning |
| --- | --- | --- | --- |
| 0 | 2 | `key_len` | Length of key, `1 … 255` |
| 2 | 2 | `val_type` | `1`=u32, `2`=u64, `3`=f32, `4`=utf8 string, `5`=bytes |
| 4 | 4 | `val_len` | Length of value in bytes, `0 … 4096` |
| 8 | `key_len` | `key` | ASCII identifier, `[a-z0-9_.]+` |
| 8+`key_len` | `val_len` | `value` | Typed value |

Records repeat until `amb_size` bytes are consumed **exactly**. A record overrunning the block is a
validation error.

### 5.1 Required keys

| Key | Type | Meaning | Required |
| --- | --- | --- | --- |
| `arch.name` | string | Architecture identifier, e.g. `aether-attn-swiglu` | Yes |
| `arch.d_model` | u32 | `d` | Yes |
| `arch.n_layers` | u32 | `L` | Yes |
| `arch.n_heads` | u32 | `H` | Yes |
| `arch.d_ff` | u32 | `d_ff` | Yes |
| `arch.vocab_size` | u32 | `V` | Yes |
| `arch.attn_window` | u32 | `W` | Yes |
| `arch.max_context` | u32 | `T_max` | Yes |
| `arch.rope_theta` | f32 | `Θ` | Yes |
| `arch.norm_eps` | f32 | `ε` | Yes |
| `arch.tie_embeddings` | u32 | `0`/`1` | Yes |
| `tok.version` | u32 | Tokenizer format version | Yes |
| `tok.type` | string | `byte-bpe` | Yes |
| `train.tokens_seen` | u64 | Informational | No |
| `train.dataset_id` | string | Manifest identifier ([`DATA_POLICY.md`](DATA_POLICY.md)) | No |
| `meta.created_utc` | string | ISO-8601, informational only | No |

**Unknown keys must be skipped, not rejected.** This is the forward-compatibility mechanism (F5).
Unknown keys in a *minor* version are ignored; an unknown **major** version is rejected outright.

### 5.2 Cross-validation of architecture keys

The loader must satisfy all of:

- `d_model % n_heads == 0` and the resulting `d_h` in `1 … 1024`
- `d_model ≤ 4096`, `n_layers ≤ 256`, `n_heads ≤ 128`, `d_ff ≤ 16384`
- `vocab_size` in `256 … 1 048 576` (a byte-level tokenizer needs ≥ 256)
- `attn_window ≥ 1` and `attn_window ≤ max_context`
- `max_context ≤ 32768`
- `norm_eps > 0` and finite
- `rope_theta > 1` and finite

Any violation → reject with a specific error code (§9).

---

## 6. Tensor Table (TT)

`tensor_count` entries of **exactly 64 bytes** each.

| Offset | Size | Field | Type | Meaning |
| --- | --- | --- | --- | --- |
| 0 | 32 | `name` | ASCII | NUL-padded; `[a-z0-9_.]+`, unique within the file |
| 32 | 1 | `dtype` | `u8` | See §6.1 |
| 33 | 1 | `rank` | `u8` | `1 … 4` |
| 34 | 2 | `reserved` | — | Must be `0` |
| 36 | 4 | `dim0` | `u32` | Slowest-varying dimension |
| 40 | 4 | `dim1` | `u32` | |
| 44 | 4 | `dim2` | `u32` | |
| 48 | 4 | `dim3` | `u32` | Fastest-varying |
| 52 | 4 | `data_offset` | `u32` | **Relative** to `data_region_offset` |
| 56 | 4 | `data_size` | `u32` | Bytes, must equal `shape × dtype_size` |
| 60 | 4 | `tensor_checksum` | `u32` | FNV-1a 32 over this tensor's bytes |

Dimensions beyond `rank` must be `1`.

### 6.1 Data types

| Value | Name | Bytes/elem | Supported in v1 |
| --- | --- | --- | --- |
| 0 | reserved | — | No |
| 1 | `f32` | 4 | **Yes** |
| 2 | `f16` | 2 | No — rejected (§6.2) |
| 3 | `bf16` | 2 | No — rejected |
| 4 | `i8` | 1 | Reserved for v1.x (flags bit 0) |
| 5 | `i4` (packed 2/elem) | 0.5 | Reserved for v1.x |
| 6 | `f64` | 8 | **Yes, but only for host tooling**; a runtime model containing `f64` tensors must be rejected unless the runtime declares support |
| 7–255 | — | — | Rejected |

**[PROPOSED]** `f16` and `bf16` are **rejected, not merely unsupported**
([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §3.1). They have no benefit on AETHER's targets, and
accepting-and-converting them would silently change numerics.

### 6.2 Tensor validation rules

For each entry, in order:

1. `name` non-empty, NUL-terminated within 32 bytes, charset valid, **unique**.
2. `dtype` supported by this parser.
3. `rank` in `1 … 4`; unused dims are `1`.
4. Every `dim_i` in `1 … 2³¹−1`.
5. **Element count computed with checked 64-bit multiplication**; overflow → reject.
6. `data_size == element_count × dtype_size`, checked without overflow.
7. `data_offset % 64 == 0` (alignment, §2).
8. `data_offset + data_size ≤ data_region_size`, checked without overflow.
9. **Tensor regions must not overlap** — checked across all entries (sort by offset, walk
   sequentially). Overlap is rejected: it would let two tensors alias and defeat checksums.
10. Every tensor named in the architecture's required set is present, with the expected rank and
    dimensions derived from §5.1 — **not** trusted from the file.

Rule 10 is the important one: the loader computes the expected shape of `blk.0.attn.wqkv` from
`d_model` and validates it, rather than allocating whatever the file claims.

### 6.3 Required tensor set (v1 architecture)

For each layer `ℓ` and the head:

| Tensor | Shape | dtype |
| --- | --- | --- |
| `tok.embed` | `[V, d]` | f32 |
| `blk.{ℓ}.attn.wqkv` | `[d, 3d]` | f32 |
| `blk.{ℓ}.attn.wo` | `[d, d]` | f32 |
| `blk.{ℓ}.mlp.wgateup` | `[d, 2·d_ff]` | f32 |
| `blk.{ℓ}.mlp.wdown` | `[d_ff, d]` | f32 |
| `blk.{ℓ}.norm1.g` | `[d]` | f32 |
| `blk.{ℓ}.norm2.g` | `[d]` | f32 |
| `out.norm.g` | `[d]` | f32 |

When `arch.tie_embeddings == 1`, **no** `out.proj` tensor exists; the output projection uses
`tok.embedᵀ`. When it is `0`, `out.proj` with shape `[d, V]` is required. A file declaring one and
containing the other is rejected.

Name format is normative: a loader that does not find a name in this exact form rejects the file
rather than guessing. Guessing is how loaders become security bugs.

---

## 7. Tokenizer Block (TB)

Length-prefixed and self-contained so the tokenizer can be versioned independently of the weights
([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §5). Layout:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | `tok_magic` = `0x54 0x4F 0x4B 0x31` (`"TOK1"`) |
| 4 | 4 | `tok_version` = 1 |
| 8 | 4 | `vocab_size` — must equal `arch.vocab_size` |
| 12 | 4 | `max_token_len` — `1 … 255` |
| 16 | 4 | `n_special` — `0 … 256` |
| 20 | 4 | `n_merges` |
| 24 | 4 | `reserved` = 0 |
| 28 | 4 | `offsets_size` |
| 32 | 4 | `strings_size` |
| 36 | 4 | `merges_size` |
| 40 | 4 | `special_size` |
| 44 | 4 | `reserved2` = 0 |
| 48 | `offsets_size` | `(vocab_size+1) × u32` offsets into the string pool |
| … | `strings_size` | concatenated token byte strings |
| … | `merges_size` | merge rules, `n_merges × (u16, u16)` |
| … | `special_size` | special-token declarations |

Validation: offsets monotonically non-decreasing, first `0`, last `== strings_size`, every
`strings_size ≤ 1 MiB`, `vocab_size` consistent with all counts
([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §5.2).

---

## 8. Integrity Block (IB)

| Offset | Size | Field | Meaning |
| --- | --- | --- | --- |
| 0 | 4 | `ib_magic` = `"INT1"` | |
| 4 | 4 | `ib_version` = 1 | |
| 8 | 4 | `n_records` | Entries following |
| 12 | 4 | `reserved` = 0 | |
| 16 | `n_records × 40` | records | See below |

Each record:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 32 | `section_name` (e.g. `header`, `amb`, `tt`, `tb`, `data`) |
| 32 | 4 | `algorithm` (`1` = FNV-1a 32, `2` = FNV-1a 64) |
| 36 | 4 | `checksum` |

**[PROPOSED]** FNV-1a rather than SHA-2: it requires no dependency, is trivially implemented in ~10
lines, and detects **corruption and truncation** — which is the actual threat here.

**Explicitly not an authenticity mechanism.** A checksum proves a file is internally consistent, not
that it came from a trusted source. AETHER makes no signature or authenticity claim in v1, and
documents this limitation rather than implying a checksum means "safe". Signing is an **[OPEN]**
question, deliberately deferred.

---

## 9. Validation sequence (normative)

A conforming loader **must** perform these steps in this order and **must not allocate based on file
contents before step 9**.

1. File length ≥ 256; read exactly 256 bytes.
2. `magic` matches. Else `E_BAD_MAGIC`.
3. `format_version == 1`. Else `E_BAD_VERSION` (report the version found).
4. `header_size == 256`; `reserved0/1/2` all zero. Else `E_BAD_HEADER`.
5. `flags == 0` (v1). Else `E_UNSUPPORTED_FLAGS`.
6. `file_size` equals the actual file length. Else `E_TRUNCATED` or `E_TRAILING_DATA`.
7. Section sizes in range; `tt_size == tensor_count × 64`; `tensor_count` in `1 … 4096`; every section
   offset computed with **checked** arithmetic and confirmed within the file.
8. `data_region_offset % 64 == 0` and `data_region_offset ≥ 256 + amb + tt + tb + ib`.
9. Parse and validate the **AMB** (§5): record structure, required keys, cross-validated architecture
   values, and the derived tensor shape expectations.
10. Parse the **TT** (§6.2) and validate every entry, including non-overlap and the required tensor
    set with the shapes derived in step 9.
11. Parse the **TB** (§7) and cross-check `vocab_size`.
12. Parse the **IB** (§8) and verify the header-level `data_checksum`, then each section checksum.
13. Read `data_region_size` and confirm it equals the sum of all `data_size` plus alignment padding.
14. **Only now** compute total required memory, compare against the configured ceiling, and allocate.
15. Stream tensor data, verifying each per-tensor checksum **as it is read**.
16. On any failure at any step: free everything, leave no partially-initialised model, and return a
    specific error code.

**[PROPOSED]** Steps 1–13 operate on metadata only and allocate nothing larger than a 64 KiB scratch
buffer. This means a malformed file cannot cause a large allocation, which is the property that
matters most for hostile input.

### 9.1 Error codes

| Code | Meaning |
| --- | --- |
| `E_BAD_MAGIC` | Not an AMC file |
| `E_BAD_VERSION` | Unsupported major version |
| `E_BAD_HEADER` | Header field inconsistent |
| `E_UNSUPPORTED_FLAGS` | Flags require a newer parser |
| `E_TRUNCATED` | File shorter than declared |
| `E_TRAILING_DATA` | File longer than declared |
| `E_BAD_SECTION` | Section offset/size out of range or overlapping |
| `E_BAD_AMB` | Architecture metadata malformed |
| `E_BAD_ARCH` | Architecture values outside supported limits |
| `E_BAD_TENSOR` | Tensor entry malformed |
| `E_TENSOR_OVERLAP` | Two tensors claim overlapping bytes |
| `E_MISSING_TENSOR` | Required tensor absent |
| `E_SHAPE_MISMATCH` | Tensor shape disagrees with architecture |
| `E_BAD_TOKENIZER` | Tokenizer block malformed |
| `E_CHECKSUM` | Integrity check failed |
| `E_TOO_LARGE` | Declared model exceeds the configured memory ceiling |
| `E_NOMEM` | Allocation failed |

A loader that cannot distinguish at least these cases is under-specified for testing malformed input.

---

## 10. Malformed-file handling

Requirements, each of which becomes a test case in Phase 6:

| Case | Required behaviour |
| --- | --- |
| Empty file / shorter than header | `E_TRUNCATED`, no allocation |
| Wrong magic | `E_BAD_MAGIC`, immediate |
| Truncation at every boundary (fuzz) | Rejected with a specific code, never a crash |
| `tensor_count = 0` or `> 4096` | `E_BAD_ARCH` / `E_BAD_TENSOR` |
| `dim` values that overflow element count | `E_BAD_TENSOR`, checked multiply |
| `data_offset + data_size` overflow | `E_BAD_TENSOR` |
| Byte count that wraps to a plausible small value | `E_OVERFLOW`, checked multiply in 64-bit |

### 8.1 Why the third row exists

A wrapped multiply does not crash — it silently produces a *smaller* number, and the smallest possible
result is **zero**, which is a perfectly valid allocation size. From
[`CPU_32BIT_RESEARCH.md`](CPU_32BIT_RESEARCH.md) §5.1, computed from AETHER's own dimensions:

```
b × H × T × T × 4 = 8 × 8 × 8192 × 8192 × 4 = 17,179,869,184
17,179,869,184 mod 2³²                        = 0
```

An unchecked 32-bit size computation for the attention score buffer at Config M's maximum context
yields a successful **zero-byte allocation** and a subsequent out-of-bounds write. This is reachable
from a syntactically valid file, which is why F2's "validate before allocate" is not sufficient on its
own: the validation itself must be performed in a width that can represent the failure.
| Overlapping tensor regions | `E_TENSOR_OVERLAP` |
| Duplicate tensor names | `E_BAD_TENSOR` |
| Tensor whose declared shape contradicts the architecture | `E_SHAPE_MISMATCH` |
| `vocab_size` in AMB ≠ TB | `E_BAD_TOKENIZER` |
| Non-zero reserved bytes | `E_BAD_HEADER` |
| Checksum mismatch | `E_CHECKSUM` |
| File with valid header, garbage body | `E_CHECKSUM`, after bounded reads only |
| Deliberate allocation bomb (huge declared dims) | `E_BAD_ARCH` before any allocation |
| Directory / FIFO / device passed as file | Opened read-only, regular-file check applied |

**The parser is a fuzzing target** ([`SECURITY_MODEL.md`](SECURITY_MODEL.md) §4). A regression corpus of
malformed files is part of the test suite, and every crash found becomes a permanent test case.

---

## 11. Forward and backward compatibility

| Change | Compatibility rule |
| --- | --- |
| New optional AMB key | Old parser skips it; new parser reads it. **Compatible** |
| New tensor, unused by old architecture | Cannot be ignored safely — requires a new `arch.name`. **Incompatible** |
| Change a tensor's shape | **Incompatible**; new `arch.name` or major version |
| New dtype (int8) | Gated on `flags` bit 0; a v1 parser rejects a file with that bit set. **Explicitly incompatible** |
| New header field | Taken from `reserved2`; a v1 parser rejects non-zero reserved bytes. **Minor-version bump** |
| Reformatted tokenizer block | `tok.version` bump; handled by the tokenizer module, not the loader |

**[PROPOSED]** There is **no** compatibility promise across major versions. A v2 parser may reject v1
files, and if it does so, it says so clearly rather than misinterpreting them.

---

## 12. Resource limits (defaults)

Configurable, with these defaults enforced before allocation:

| Limit | Default | Rationale |
| --- | --- | --- |
| Max file size | 512 MiB | Bounds a pathological file |
| Max `tensor_count` | 4096 | |
| Max total parameters | 1 × 10⁹ | Far above the 10 M budget; a typo cannot become a 64 GiB allocation |
| Max single tensor | 64 MiB | |
| Max `amb_size` | 64 KiB | |
| Max `tb_size` | 8 MiB | |
| Max `ib_size` | 1 MiB | |
| Max total runtime memory | 512 MiB | [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §2 |

**[PROPOSED]** Limits are enforced by the loader itself, not by the caller, and a caller may only
*lower* them. This matters because the runtime is the component exposed to untrusted files.

---

## 13. Implementation notes for the loader

- **No `malloc` on file-derived sizes before validation completes** (§9 step 14).
- All size arithmetic uses `uint64_t` internally even on 32-bit, since `size_t` there is 32 bits and
  a `u32 + u32` can wrap. Values are checked against `SIZE_MAX` before narrowing.
- Every `read` is checked for short reads; a short read is an error, never a retry loop without bound.
- **No `mmap` assumptions**: the loader works identically over a stream, so a runtime without `mmap`
  can still load models.
- The loader takes a `const uint8_t*` plus length where possible, so it is testable without a
  filesystem and fuzzable in-process.
- **No alignment assumption on the input buffer.** Header parsing is done by explicit little-endian
  byte assembly, not by casting a pointer to a struct — struct layout is not guaranteed across
  compilers and would reintroduce endianness and padding bugs.

---

## 14. Unresolved questions

1. Should v1 add a signature field, or is integrity-only acceptable? **Proposed: integrity-only**,
   with authenticity documented as out of scope. **[OPEN]**
2. Is FNV-1a adequate, or is a small SHA-256 implementation worth its ~200 lines? **[OPEN]** — FNV
   detects accidents; SHA-256 would also resist deliberate collision. Whether that matters depends on
   the threat model, which for local model files is weak.
3. Should int8 tensor storage be v1 or v1.x? **Proposed: v1.x**, after int8 has been evaluated
   ([`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §8).
4. Should the tokenizer block live in the model file at all, or be a separate sidecar? Embedding it
   keeps a model self-contained, at the cost of coupling two version stories. **Proposed: embedded**,
   with independent version fields. **[OPEN]**
5. Does the 64-byte alignment of every tensor waste meaningful space for small tensors (norm gains of
   `d` floats)? At `d = 256`, a norm gain is 1024 bytes and rounds to 1024 — no waste. At `d = 32`,
   however, waste is real. **Proposal: keep 64-byte alignment**, since small models are not
   storage-constrained ([`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §3). **[OPEN]**
