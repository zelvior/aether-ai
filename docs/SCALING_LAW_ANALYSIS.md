# AETHER — Scaling Law Analysis

Status: **Extrapolation, treated with explicit suspicion.** Every number in §3–§5 is a published fit
evaluated **far outside the range it was fitted on**. This document exists to state what those fits *predict*
and, more importantly, why those predictions may not hold at AETHER's scale.

Related: [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §5.1 (the regime question) ·
[`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) (how it is tested) ·
[`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) (compute) · [`RESEARCH_REFERENCES.md`](RESEARCH_REFERENCES.md) `[S9]` `[S51]`

---

## 1. The two published fits, and how they disagree

| Fit | Source | Claimed allocation |
| --- | --- | --- |
| Kaplan et al. 2020 | `[S51]` | Scale `N` much faster than `D`; large models, modest data |
| Chinchilla 2022 | `[S9]` | Scale `N` and `D` **equally**; ≈ **20 tokens/parameter** |

`[S9]` explicitly revised `[S51]`, identifying methodological issues in the earlier fit (notably learning-rate
schedule effects at different token budgets). **AETHER treats `[S9]` as the better-supported fit** and uses its
form.

This is worth stating plainly: the two most-cited scaling papers reach materially different conclusions about
how to allocate a fixed budget, and the later one supersedes the earlier. Anyone citing "scaling laws" without
saying which is citing a moving target.

### 1.1 The functional form

```
L(N, D) = E + A/N^α + B/D^β
```

| Term | Meaning |
| --- | --- |
| `E` | **Irreducible** loss — the entropy of natural language itself |
| `A/N^α` | Loss attributable to finite model capacity |
| `B/D^β` | Loss attributable to finite data |

Chinchilla reports approximately `E = 1.69`, `α ≈ 0.34`, `β ≈ 0.28` (in nats/token, for their tokenizer).

---

## 2. The extrapolation problem, quantified first

Before using any fit, AETHER must state how far outside its fitted range it is sitting.

| Quantity | Chinchilla's fitted range | Config M | Ratio |
| --- | --- | --- | --- |
| Model size | from ~70 M parameters | **8.43 M** | **8.3× below** |
| Training data | from ~1.4 B tokens | 84.3 M at 10 tok/param | **17× below** |

**AETHER is more than an order of magnitude below the smallest point in both dimensions.**

`[S9]` fitted a power law across its range; AETHER asks that law to extrapolate downward by 8–17×. There is no
theoretical guarantee a power law continues, and §5 discusses the specific reason it may not.

**[PROPOSED]** Any sentence in AETHER's documentation that predicts loss using these coefficients must carry
this caveat. A prediction from an extrapolated fit is **a hypothesis**, not an estimate with an error bar.

---

## 3. What the fits predict at AETHER's scale

Evaluating `L(N,D) = 1.69 + 406.4/N^0.34 + 410.7/D^0.28` at 10 tokens/parameter:

| Config | `N` | `D` | Predicted `L` (nats/token) | `E/L` |
| --- | --- | --- | --- | --- |
| T | 228,672 | 2,286,720 | **14.62** | 12 % |
| N | 1,840,256 | 18,402,560 | **8.50** | 20 % |
| M | 8,425,728 | 84,257,280 | **5.97** | **28 %** |

### 3.1 The uncomfortable structure of these numbers

At Config M, **28.3 % of the predicted loss is irreducible** — the `E` term. Breaking the remainder down:

| Term | Value (nats) | Share of total |
| --- | --- | --- |
| `E` (irreducible) | 1.690 | 28.3 % |
| `A/N^0.34` (capacity) | **1.796** | 30.1 % |
| `B/D^0.28` (data) | **2.479** | 41.6 % |
| **Total** | **5.965** | |

**The data term is larger than the capacity term.** By this fit, Config M is *under-trained relative to its
capacity* even at 10 tokens/parameter, which is consistent with `[S9]`'s ~20 tokens/parameter recommendation
and is exactly what E3 ([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) §5) tests.

### 3.2 The gap between T and M

The fit predicts a drop from 14.62 to 5.97 nats — a factor of **2.45**. **That is the "if power law holds" case**,
and it is a large predicted improvement from Config T to Config M.

If E1 measures a *much smaller* drop, the power law has broken and AETHER is in a threshold or saturation
regime. **E1 is therefore a direct test of these coefficients**, not merely of a qualitative regime.

---

## 4. What the fit says about AETHER's key choices

### 4.1 The tokens-per-parameter question

| Tokens/param | `D` at Config M | Predicted `L` | Δ vs 10 |
| --- | --- | --- | --- |
| 5 | 42,128,640 | 6.496 | **+0.531** |
| 10 | 84,257,280 | 5.965 | — |
| 20 | 168,514,560 | 5.528 | **−0.437** |
| 40 | 337,029,120 | 5.168 | **−0.797** |

Each doubling of data buys **0.44–0.53 nats**, with the return diminishing as `D^−0.28` requires. **Holding compute fixed, the question is whether those 0.53 nats are
better bought by more data or more parameters** — and `[S9]`'s answer is that at this scale they are roughly
balanced, which is why it recommends 20.

**[PROPOSED]** AETHER's 10 tokens/parameter is a deliberate under-investment in data, justified only by the
assumption that a modest corpus is what is obtainable. That is a *resource* argument, not a modelling one, and
it should be labelled as such.

### 4.2 The vocabulary question

These fits are per-token for a specific tokenizer. AETHER's `V = 8192` is much smaller than Chinchilla's, so
**its per-token loss is not directly comparable** — the same text becomes more tokens, lowering per-token
entropy while raising per-byte cost.

This is precisely why [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) mandates bits-per-byte
([`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md) §10.2). **The numbers in §3 are per-token and
should not be compared to any published BPC figure.**

---

## 5. Why the power law may break at AETHER's scale

Four mechanisms, each with a different consequence. **AETHER does not know which applies.**

### 5.1 Capability thresholds

`[S34]` found chain-of-thought reasoning *emerges* between roughly 10¹⁰ and 10¹¹ parameter models. If specific
capabilities appear abruptly, loss may continue smoothly downward while **capability stays at zero**. A
smooth loss curve would then be actively misleading about usefulness.

### 5.2 The irreducible term is not constant

`E` represents language entropy, and it depends on the **distribution**. `[S10]` (TinyStories) shows that a
narrow, simple corpus has dramatically lower entropy than general web text. AETHER's corpus will not be
general web text.

**If AETHER trains on a narrow corpus, its `E` is lower and the whole curve shifts down** — but the capability
it acquires is correspondingly narrow. Both effects are real and they point in opposite directions on the
"is this useful?" question.

### 5.3 Tokenizer leakage

`D` counts tokens. At `V = 8192`, a token carries fewer bytes than at `V = 50000`. So "10 tokens/parameter"
encodes **less text** than the same ratio at a larger vocabulary. The fit's `D` axis is not
vocabulary-normalised, and comparing raw token counts across vocabularies is unsound.

**[PROPOSED]** Restate the data budget in **bytes** wherever it is used for planning.

The two units are easy to conflate. 84.3 M tokens corresponds to roughly **390 MB of raw text** at
1.3 tokens/word and 6 bytes/word — the figure [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) §8
gives. If AETHER's tokenizer achieves ≈ 3 bytes/token, the same 84.3 M tokens would instead cover only
≈ **250 MB** of text. **Which applies is unknown until the tokenizer is trained and the corpus measured**
— [`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §3 makes measuring that ratio a Phase 3 deliverable. Until
then the corpora size and the token budget should not be used interchangeably.

### 5.4 Finite-width effects below the fit

The fits were established where `d ≥ 768`. AETHER uses `d = 256`. Embedding-table effects, LayerNorm/RMSNorm
behaviour, and the relative weight of the irreducible term are all different at small width, and none of it is
captured by a two-parameter power law.

---

## 6. What would make the extrapolation trustworthy

| Requirement | AETHER status |
| --- | --- |
| Measures loss at ≥ 3 sizes spanning ≥ 10× | **E1 does this** |
| Same corpus, tokenizer, objective | Design requires it |
| Seed variance bounded | **E2 does this** |
| Data budget varied to locate the optimum | **E3 does this** |
| Reported in a vocabulary-independent unit | **BPC, mandated** |

**The six-day programme in [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) produces AETHER's own scaling curve.**
Once it exists, §3's extrapolations should be discarded in favour of measured values — and the measured
exponents, even if noisy, will be more informative than a fit from a different regime.

---

## 7. The prediction AETHER is making, stated falsifiably

This is the point of the exercise. AETHER commits, in advance, to:

> **If the power law holds, Config M trained at 10 tokens/parameter will reach a held-out BPC substantially
> better than Config N, with a gap of roughly the magnitude predicted in §3.2 — a factor of about **1.4×**
> between N and M (8.50 → 5.97 nats), and about **2.45×** between T and M.**

And the falsification conditions:

| Outcome | Conclusion |
| --- | --- |
| Gap ≈ predicted | Power law holds; scale `N` is the path |
| Gap much smaller | Saturation; Config M is near a ceiling |
| Gap much larger | Either the fit is wrong, or AETHER's regime is genuinely different — investigate |
| Both at chance on capability tasks despite good BPC | **Loss is not capability** — the threshold regime applies |

The fourth row is the one that would most change the project, and it is the one a loss curve cannot rule out.

---

## 7A. How good is the `6ND` design estimate, exactly?

`6ND` is the workhorse constant for training-cost estimates everywhere in the project and in the literature
(`[S9]`, `[S51]`). It is worth knowing precisely how far it is from the exact count, because AETHER uses it to
decide whether a run is affordable.

`tools/phase2_calc.py:flops_vs_6nd()` reconciles the exact forward count against `2ND` and **asserts** the
identity:

```
exact = 2ND  +  attention matmuls  −  2 × (norm parameters) × T
```

Both correction terms are real:

| Correction | Direction | Reason |
| --- | --- | --- |
| Attention score/AV matmuls | `6ND` **under**-counts | Data-dependent, not parameter-borne |
| Norm parameters | `6ND` **over**-counts | `2d` params per layer, but only 2 FLOPs each |

The second term needs care: each RMSNorm parameter costs **2 FLOPs** per token (a multiply and an accumulate),
not 1, and there are two norms per layer plus a final norm.

### 7A.1 Measured error at AETHER's training lengths

| Config | Exact forward FLOPs | `2ND` | Ratio |
| --- | --- | --- | --- |
| T | 62,685,184 | 58,540,032 | 1.071 |
| N | 992,083,968 | 942,211,072 | 1.053 |
| M | 9,429,843,968 | 8,627,945,472 | **1.093** |

At `T = 512` with a window of 256, `6ND` is **9.3 % low** — acceptable for planning.

### 7A.2 But the error is not bounded — it grows with `T`

Recomputing Config M at full attention as the sequence length grows:

| `T` | Exact / `2ND` |
| --- | --- |
| 128 | 1.031 |
| 512 | 1.124 |
| 2,048 | **1.498** |
| 8,192 | **2.991** |

**At `T = 8192`, `6ND` understates forward cost by a factor of 3.** This is the well-known property that
`6ND` is exact only when `T ≪ d`; AETHER's `T = 2d` is already in the regime where it drifts, and long-context
claims would be badly mispriced by it.

**[PROPOSED]** Any AETHER cost figure for `T > 1024` must come from `prefill_macs()`, never from `6ND`. The
scaling-law literature's compute axis is `6ND`-based, which means **published compute-optimal budgets are
systematically optimistic for long-context training** — a caveat that applies to `[S9]` itself and is rarely
stated.

---

## 8. Unresolved questions

1. Do the Chinchilla coefficients extrapolate 8–17× downward? **E1 answers this.** **[OPEN]**
2. Is AETHER's `E` lower than 1.69 because of a narrower corpus, and by how much? **Requires the corpus.** **[OPEN]**
3. Does the `D` axis need byte-normalisation to be meaningful across tokenizers? **Proposed: yes — report both.** **[OPEN]**
4. Is there a capability threshold between 1.8 M and 8.4 M parameters? **Unmeasurable with BPC alone.** **[OPEN]**
5. Should AETHER target 20 tokens/parameter despite the data cost? **Depends on E3.** **[OPEN]**
6. Do the exponents `α = 0.34`, `β = 0.28` differ at small width, and in which direction? **[OPEN]**
7. How much does the `6ND` long-context error (§7A.2) bias published compute-optimal recipes? **Unquantified.** **[OPEN]**

---

## 9. Status summary

| Item | Status |
| --- | --- |
| Kaplan vs Chinchilla disagreement | **Established** — `[S9]` supersedes `[S51]` |
| Functional form `E + A/N^α + B/D^β` | **Established** |
| Extrapolation distance (8–17× below fit) | **Derived** — §2, and it is large |
| Predicted loss at three configs | **Extrapolated**, §3 — treat as hypothesis |
| Irreducible share at M (28 %) | **Extrapolated** |
| Four mechanisms that could break the law | **Reasoned** — §5 |
| `6ND` error at `T=512`: 9.3 % low | **Derived** — §7A.1, asserted in tool |
| `6ND` error at `T=8192`: 3.0× low | **Derived** — §7A.2 |
| AETHER's own scaling curve | **Does not exist** — E1 produces it |
| Any measurement | **None.** |
