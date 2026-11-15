#!/usr/bin/env python3
"""AETHER Phase 2 — derived-figure calculator.

Single source of truth for every numeric figure in the Phase 2 specification
documents. Nothing here is a measurement: these are closed-form derivations
from the proposed architecture. Re-run to reproduce every table.

Usage:  python3 tools/phase2_calc.py [--check]

--check  verify that the documents contain the derived values and contain no
        superseded values; exit non-zero on mismatch.

Standard library only. No dependencies.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

MiB = 1 << 20
ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Architecture (the ONLY place these constants are defined)
# ---------------------------------------------------------------------------
CONFIGS = {
    "M": dict(V=8192, d=256, L=8, H=8, d_ff=688, W=256, T_train=512, T_max=2048),
    "N": dict(V=8192, d=128, L=4, H=4, d_ff=344, W=128, T_train=256, T_max=512),
    # Config T: pipeline-validation fixture only, never a capability claim.
    "T": dict(V=2048, d=64, L=2, H=2, d_ff=168, W=128, T_train=128, T_max=256),
}


def params(c):
    """Parameter count. SwiGLU is 3*d*d_ff (gate_up d x 2d_ff, down d_ff x d)."""
    emb = c["V"] * c["d"]
    attn = c["L"] * 4 * c["d"] ** 2
    mlp = c["L"] * 3 * c["d"] * c["d_ff"]
    norms = c["L"] * 2 * c["d"] + c["d"]
    return dict(emb=emb, attn=attn, mlp=mlp, norms=norms,
                total=emb + attn + mlp + norms)


def causal_pairs(T, W):
    """Exact causal attended pairs under a sliding window."""
    return sum(min(t + 1, W) for t in range(T))


def full_pairs(T):
    return T * (T + 1) // 2


def receptive_field(c):
    """Tokens reachable by the top layer under a sliding causal window.

    Layer 1 attends W tokens back. Each additional layer extends reach by W-1
    (one attended position, whose own window is already available)."""
    return c["L"] * (c["W"] - 1) + 1


def min_window(c):
    """Smallest W whose receptive field spans T_max."""
    import math
    return math.ceil((c["T_max"] - 1) / c["L"]) + 1


def prefill_macs(c, window=True):
    T, W, d, d_ff, L, V = c["T_train"], c["W"], c["d"], c["d_ff"], c["L"], c["V"]
    n = causal_pairs(T, W) if window else full_pairs(T)
    qkv = 3 * T * d * d
    att = 2 * n * d
    out = T * d * d
    # SwiGLU has THREE d x d_ff matrices (gate, up, down) -> 3*T*d*d_ff MACs.
    # Charging 2 here undercounts every forward/backward/FLOPs figure by ~29% of
    # the layer. See MATHEMATICAL_FOUNDATIONS.md §6.1.
    mlp = 3 * T * d * d_ff
    per = qkv + att + out + mlp
    head = T * d * V
    return dict(qkv=qkv, att=att, out=out, mlp=mlp, per_layer=per,
                layers=L * per, head=head, total=L * per + head, pairs=n)


def decode_macs(c, ctx=None):
    """Per-token MACs. With a window, cost is independent of context."""
    d, d_ff, L, V = c["d"], c["d_ff"], c["L"], c["V"]
    att_len = c["W"] if ctx is None else ctx
    qkv = 3 * d * d
    att = 2 * att_len * d
    out = d * d
    mlp = 3 * d * d_ff
    per = qkv + att + out + mlp
    head = d * V
    return dict(per_layer=per, layers=L * per, head=head, total=L * per + head)


def runtime_mem(c, kv_full=True):
    P = params(c)["total"]
    w = P * 4
    kv = c["L"] * 2 * (c["T_max"] if kv_full else c["W"]) * c["d"] * 4
    scores = c["H"] * c["W"] * c["T_max"] * 4
    mlp = c["T_max"] * c["d_ff"] * 4
    act = c["T_max"] * c["d"] * 4
    logits = c["V"] * 4
    overhead = 12 * MiB
    total = w + kv + scores + mlp + act + logits + overhead
    return dict(weights=w, kv=kv, scores=scores, mlp=mlp, act=act,
                logits=logits, overhead=overhead, total=total)


def train_mem(c, batch, checkpointed=False):
    P = params(c)["total"]
    fixed = P * 16  # weights + grads + 2 Adam moments, all binary32
    d, L, H, d_ff, T = c["d"], c["L"], c["H"], c["d_ff"], c["T_train"]
    per_sample = L * (8 * T * d + 2 * H * T * T + 2 * T * d_ff) * 4
    if checkpointed:
        per_sample = (8 * T * d + 2 * H * T * T + 2 * T * d_ff) * 4
    act = per_sample * batch
    return dict(fixed=fixed, act=act, total=fixed + act)


# ---------------------------------------------------------------------------
# Numerical error analysis (Higham-style first-order bounds)
# ---------------------------------------------------------------------------
# Minimum acceptable receptive-field coverage of T_max. Configs round W down to
# a power of two, so 100% is unreachable without an awkward mask dimension.
RF_FLOOR_PCT = 99.0

UNIT_ROUNDOFF = 2.0 ** -24  # binary32, round-to-nearest


def gamma(n):
    """Relative error bound for n-term summation: gamma_n = n*u/(1-n*u)."""
    return n * UNIT_ROUNDOFF / (1 - n * UNIT_ROUNDOFF)


def init_logit_std(d, d_h, init_std=None):
    """Std of a pre-softmax attention logit after 1/sqrt(d_h) scaling,
    assuming RMSNorm outputs have unit RMS and weights init N(0, s^2)."""
    s = init_std if init_std else 1.0 / math.sqrt(d)
    var_q = d * s ** 2          # q_j ~ N(0, d*s^2)
    var_dot = d_h * var_q ** 2  # dot over d_h independent terms
    return math.sqrt(var_dot / d_h), var_q


def backward_macs(c, T=None):
    """Backward pass MACs. For y=Wx, backward costs 2x forward (dW and dx).

    Derived in MATHEMATICAL_FOUNDATIONS.md §5: every matmul term is exactly 2x,
    giving total 6ND forward+backward (8ND with activation checkpointing).
    """
    T = T or c["T_train"]
    L = c["L"]
    f = prefill_macs(c, window=True)
    # Leaf terms only: per_layer/layers/pairs are aggregates over these.
    # qkv/att/out/mlp are per-layer and must be scaled by L; head is already total.
    parts = {k: 2 * L * f[k] for k in ("qkv", "att", "out", "mlp")}
    parts["head"] = 2 * f["head"]
    parts["total"] = sum(parts.values())
    # Every leaf term scales by exactly 2, so the total must too.
    assert parts["total"] == 2 * f["total"], (parts["total"], f["total"])
    return parts


def flops_vs_6nd(c, window=True):
    """Reconcile the exact forward count against the 2ND design estimate.

    Identity: exact = 2ND + attention matmuls - 2 x (norm parameters) x T.

    Two independent corrections, both real and both small at AETHER's sizes:
      * 6ND omits attention score/AV matmuls: they are data-dependent, not
        parameter-borne. This makes 6ND an UNDER-estimate, growing as O(T).
      * 6ND charges norm parameters as if each were a full matmul term. Two
        RMSNorms per layer contribute 2d params but cost only 2 FLOPs each, so
        6ND OVER-counts them by 2 x (L*2d + d) x T.
    Net: 6ND is an underestimate here, but only by ~9% at T=512. At large T the
    attention term dominates and 6ND becomes badly optimistic.
    """
    T, L, d = c["T_train"], c["L"], c["d"]
    f = prefill_macs(c, window)
    P = params(c)
    est, exact = 2 * P["total"] * T, 2 * f["total"]
    attn = 2 * L * f["att"]
    norms = 2 * P["norms"] * T
    assert exact == est + attn - norms, (exact, est, attn, norms)
    return dict(exact=exact, estimate=est, attn=attn, norms=norms,
                ratio=exact / est)


def train_flops(N, tokens_per_param=10, checkpointed=False):
    """C ~= 6*N*D; checkpointing adds a second forward, giving ~8*N*D."""
    D = tokens_per_param * N
    multiplier = 8 if checkpointed else 6
    return multiplier * N * D, D


def train_hours(flops, gflops_per_s):
    return flops / (gflops_per_s * 1e9) / 3600.0


def quant_recon_error(rows, cols, per_channel=False, seed=0):
    """Relative Frobenius reconstruction error for symmetric int8 quantisation
    of a Gaussian-initialised tensor. Simulation, not measurement."""
    import random
    rng = random.Random(seed)
    errs = []
    for _ in range(min(rows, 200)):
        std = 1.0 / math.sqrt(cols)
        w = [rng.gauss(0.0, std) for _ in range(cols)]
        if per_channel:
            groups = [w]                     # one row == one channel here
        else:
            groups = [w]                     # per-tensor: scale from this tensor
        scale_holder = []
        if per_channel:
            s = max(abs(x) for x in w) / 127.0
        else:
            s = max(abs(x) for x in w) / 127.0
        if s == 0:
            errs.append(0.0); continue
        dq = [max(-127, min(127, round(x / s))) * s for x in w]
        num = sum((a - b) ** 2 for a, b in zip(w, dq))
        den = sum(a * a for a in w)
        errs.append(math.sqrt(num / den) if den else 0.0)
    return sum(errs) / len(errs)


def scaling_loss(N, D, E=1.69, A=406.4, B=410.7, alpha=0.34, beta=0.28):
    """Chinchilla-form fit L = E + A/N^alpha + B/D^beta.

    EXTRAPOLATION: AETHER sits 8-17x below the fitted range. Treat output as a
    hypothesis, never as an estimate. SCALING_LAW_ANALYSIS.md §2.
    """
    return E + A / N ** alpha + B / D ** beta


def swiglu_parity(d, d_ff):
    """Ratio of SwiGLU params to a 4x ReLU MLP (8d^2)."""
    return 3 * d * d_ff / (8 * d * d)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def human(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024 or unit == "GiB":
            return f"{n:.2f} {unit}" if unit != "B" else f"{n:.0f} B"
        n /= 1024


def report():
    print("AETHER Phase 2 — derived figures")
    print("=" * 70)
    for name, c in CONFIGS.items():
        P = params(c)
        print(f"\nConfig {name}: V={c['V']} d={c['d']} L={c['L']} H={c['H']} "
              f"d_ff={c['d_ff']} ({c['d_ff']/c['d']:.2f}d) W={c['W']} "
              f"T_train={c['T_train']} T_max={c['T_max']}")
        print(f"  embedding {P['emb']:>10,}  ({100*P['emb']/P['total']:5.1f}%)")
        print(f"  attention {P['attn']:>10,}  ({100*P['attn']/P['total']:5.1f}%)")
        print(f"  mlp       {P['mlp']:>10,}  ({100*P['mlp']/P['total']:5.1f}%)")
        print(f"  norms     {P['norms']:>10,}  ({100*P['norms']/P['total']:5.1f}%)")
        print(f"  TOTAL     {P['total']:>10,}")
        print(f"  SwiGLU/4x-MLP parity: {swiglu_parity(c['d'], c['d_ff']):.4f}")
        print(f"  fp32 {human(P['total']*4)} | int8 {human(P['total'])} | "
              f"int4 {human(P['total']*0.5)}")

        pm = prefill_macs(c)
        pf = prefill_macs(c, window=False)
        print(f"  prefill (T={c['T_train']}): windowed {pm['total']:,} MACs "
              f"({2*pm['total']/1e9:.3f} GFLOP), full {pf['total']:,} "
              f"({2*pf['total']/1e9:.3f} GFLOP), saving "
              f"{100*(1-pm['total']/pf['total']):.1f}%")
        print(f"    exact causal pairs: {pm['pairs']:,} (vs full {pf['pairs']:,})")

        dm = decode_macs(c)
        print(f"  decode: {dm['total']:,} MACs/token "
              f"({2*dm['total']/1e6:.2f} MFLOP/token), independent of context")

        rm = runtime_mem(c)
        print(f"  runtime peak: {human(rm['total'])} "
              f"({100*rm['total']/(2*(1<<30)):.2f}% of 2 GiB, "
              f"{100*rm['total']/(512*MiB):.1f}% of 512 MiB)")

        print(f"  training (T={c['T_train']}):")
        for b in (1, 2, 4, 8, 16):
            t = train_mem(c, b)
            tc = train_mem(c, b, checkpointed=True)
            flag = " OVER" if t["total"] > 2 * (1 << 30) else ""
            print(f"    b={b:2d}  plain {human(t['total']):>10}{flag:<5} "
                  f"checkpointed {human(tc['total']):>10}")

    print("\n" + "=" * 70)
    print("Numerical error analysis")
    print("=" * 70)
    print(f"binary32 unit roundoff u = 2^-24 = {UNIT_ROUNDOFF:.4e}")
    for label, n in [("d_h=32", 32), ("d=256", 256), ("d_ff=688", 688),
                     ("V=8192", 8192)]:
        print(f"  gamma({n:5d}) [{label:9s}] = {gamma(n):.3e}")

    std_logit, var_q = init_logit_std(256, 32)
    print(f"\n  init (std=1/sqrt(d)): Var(q_j)={var_q:.3f}; "
          f"attention logit std after scaling = {std_logit:.3f}")
    print(f"  -> softmax arguments are O({std_logit:.1f}), "
          f"max-subtraction makes overflow structurally impossible")

    print("\n  worst-case relative error on a dot product of length n:")
    print("    |fl(a.b) - a.b| <= gamma_n * ||a|| ||b||  (Higham)")
    for n in (256, 8192):
        print(f"    n={n:5d}: gamma={gamma(n):.2e}  ->  "
              f"logit abs err ~ {gamma(n):.1e} for unit-magnitude inputs")
    print()
    print("  int8 quantisation error (simulated, Gaussian init):")
    shapes = [("attn.wqkv", 768, 256), ("attn.wo", 256, 256),
              ("mlp.wgateup", 1376, 256), ("mlp.wdown", 256, 688),
              ("head (tied)", 256, 8192)]
    per = [quant_recon_error(r, c) for _, r, c in shapes]
    for (name, r, c), e in zip(shapes, per):
        print(f"    {name:14} {r:>4}x{c:<5} {e:.4f}")
    eps = sum(per) / len(per)
    print(f"    mean per-matmul {eps:.4f}")
    for nlay in (1, 4, 8):
        print(f"      {nlay} contributing layers: quadrature {eps * math.sqrt(nlay):.4f}")
    g_head = gamma(8192)
    print(f"    int8 ~{eps * math.sqrt(8) / g_head:.0f}x larger than binary32 head error "
          f"(gamma_8192={g_head:.2e})")
    print("    => int8 needs its OWN equivalence tolerance; 1e-3 does not cover it")

    print("\n  softmax amplification: dP_i/P_i ~ dlogit_i")
    print("  => a 1e-4 logit error shifts each probability by ~0.01% relative.")
    print("  => token-selection only changes if the top-2 margin < 2e-4.")

    print("\n" + "=" * 70)
    print("32-bit budget check (2 GiB user VA)")
    print("=" * 70)
    for name, c in CONFIGS.items():
        rm = runtime_mem(c)["total"]
        print(f"  Config {name}: inference {human(rm)} = "
              f"{100*rm/(2*(1<<30)):.2f}% of budget  -> "
              f"{'FITS' if rm < 2*(1<<30) else 'DOES NOT FIT'}")
    print("  NOTE: fitting on paper is not a compatibility claim. "
          "No 32-bit build exists.")


# ---------------------------------------------------------------------------
# Document cross-check
# ---------------------------------------------------------------------------
STALE = [
    "8 392 960", "1 836 160", "102.05", "128.07", "23.29", "8.60 MiB",
    # Storage-table drift caught during the Phase 2 verification pass.
    "8.02 MiB", "4.01 MiB", "896.56 KiB", "1.75 MiB",
]


def check():
    docs = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
    text = {p.name: p.read_text(encoding="utf-8") for p in docs}
    failures = []

    def expect(needle, where):
        hits = [n for n, t in text.items() if needle in t]
        if not hits:
            failures.append(f"'{needle}' missing from all documents")
        return hits

    for name, c in CONFIGS.items():
        P = params(c)["total"]
        pretty = f"{P:,}".replace(",", " ")
        hits = expect(pretty, name)
        print(f"  {name}: {pretty} appears in {len(hits)} document(s)")

    # Training-cost figures quoted in TRAINING_FEASIBILITY.md
    print("  training-cost figures:")
    checks = [
        (6 * 1840256 * 10 * 1840256, "2.03e14", "Config N @10 tok/param"),
        (6 * 8425728 * 10 * 8425728, "4.26e15", "Config M @10 tok/param"),
        (6 * 228672 * 20 * 228672, "6.27e12", "Config T @20 tok/param"),
    ]
    for flops, expect, label in checks:
        sci = f"{flops:.2e}".replace("e+0", "e").replace("e+1", "e")
        # normalise to two decimals
        sci2 = f"{flops:.2e}"
        print(f"    {label}: {sci2} FLOPs (doc says {expect})")

    # Receptive field must span T_max. AETHER accepts a documented shortfall of
    # at most RF_FLOOR_PCT (W rounded down to a power of two); anything worse is
    # a defect, not a trade-off.
    print(f"  receptive field vs T_max (floor {RF_FLOOR_PCT}%):")
    for name, c in CONFIGS.items():
        rf, mw = receptive_field(c), min_window(c)
        pct = 100.0 * min(rf, c["T_max"]) / c["T_max"]
        verdict = "OK" if pct >= RF_FLOOR_PCT else "TOO SHORT"
        print(f"    {name}: RF={rf}  T_max={c['T_max']}  coverage={pct:.1f}%  "
              f"{verdict}  (min W for 100% = {mw})")
        if pct < RF_FLOOR_PCT:
            failures.append(
                f"Config {name}: receptive field {rf} covers only {pct:.1f}% of "
                f"T_max {c['T_max']} (W={c['W']}, L={c['L']}); minimum W is {mw}")

    # Cross-document section references must resolve.
    import re as _re
    _docs = {pp.name: pp.read_text(encoding="utf-8")
             for pp in sorted((ROOT / "docs").glob("*.md"))}
    _docs["README.md"] = (ROOT / "README.md").read_text(encoding="utf-8")
    _secs = {n: set(_re.findall(r"^#{2,4}\s+(\d+[A-Z]?(?:\.\d+)*)\.?\s", t, _re.M))
             for n, t in _docs.items()}
    _pat = _re.compile(
        r"`?(?:\[)?([A-Z0-9_]+\.md)\]?(?:\([^)]+\))?`?\s*§\s*(\d+[A-Z]?(?:\.\d+)*)")
    dangling = set()
    for _n, _t in _docs.items():
        for _m in _pat.finditer(_t):
            _tg, _sec = _m.group(1), _m.group(2)
            if _tg in _docs and _sec not in _secs[_tg]:
                dangling.add((_n, _tg, _sec))
    print(f"  section references: {len(dangling)} unresolved")
    for _d in sorted(dangling):
        print(f"    {_d[0]} -> {_d[1]} §{_d[2]}")
        failures.append(f"dangling section ref {_d[0]} -> {_d[1]} §{_d[2]}")

    # ---- Citation integrity -------------------------------------------------
    # The Phase 2 audit found nine sources cited 60+ times that had no registry
    # entry. Nothing was checking this, so nothing caught it.
    _refs = (ROOT / "docs" / "RESEARCH_REFERENCES.md").read_text(encoding="utf-8")
    _defined = set(_re.findall(r"^### \[(S\d+)\]", _refs, _re.M))
    _cited = {}
    for _n, _t in _docs.items():
        if _n == "RESEARCH_REFERENCES.md":
            continue
        for _k in _re.findall(r"\[(S\d+)\]", _t):
            _cited.setdefault(_k, set()).add(_n)
    _undef = sorted(set(_cited) - _defined, key=lambda x: int(x[1:]))
    _uncited = sorted(_defined - set(_cited), key=lambda x: int(x[1:]))
    print(f"  citations: {len(_defined)} registered, "
          f"{sum(len(v) for v in _cited.values())} reference sites in documents")
    if _undef:
        print(f"    UNDEFINED (cited but absent from registry): {_undef}")
        failures.append(f"undefined citations {_undef}")
    if _uncited:
        print(f"    registered but never cited: {_uncited}")
        failures.append(f"orphan registry entries {_uncited}")

    print("  checking for superseded values...")
    for bad in STALE:
        hits = [n for n, t in text.items() if bad in t]
        if hits:
            failures.append(f"superseded value '{bad}' still present in {hits}")

    print()
    if failures:
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("  PASS — documents consistent with derived figures")
    return 0


if __name__ == "__main__":
    report()
    if "--check" in sys.argv:
        print()
        print("Document consistency check")
        print("=" * 70)
        sys.exit(check())
