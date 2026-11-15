# AETHER — Annotated Research References

Status: **Reference database, not results.** Every entry below was checked to exist at the stated
identifier during Phase 2. AETHER does **not** claim to have reproduced or independently validated any
reported result. Where a paper is a preprint, it is labelled as such.

This document is the single annotated registry of source identifiers used across the AETHER
documentation. The `[S<n>]` keys are global.

`[S1]`–`[S28]` were first established in [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §8 and are
re-stated here with the full eight-field annotation that the survey does not carry. Where the two
differ in wording they are the same source; the identifier is authoritative. `[S29]`–`[S51]` are
introduced by this document for the first time.

**Numbering gaps are deliberate and must not be closed up.** `[S25]` was withdrawn during Phase 2 (a
LoRA reference that did not fit the project's from-scratch constraint) and `[S35]` was never assigned.
Renumbering would silently change the meaning of every existing citation, so the gaps stay.

---

## 0. How to read an entry

Every entry carries the eight fields required for a citable source:

| Field | Meaning |
| --- | --- |
| **Title** | Exact published title |
| **Authors** | Author list as published |
| **Year / venue** | Publication year; venue and peer-review status if any |
| **Identifier** | arXiv ID, DOI, or other stable locator |
| **Contribution** | What the paper actually establishes |
| **Relevance to AETHER** | Why it is cited, and where |
| **Limitations / assumptions** | What the paper does **not** show, and the conditions it assumed |

Two conventions are load-bearing:

- **Preprint** means arXiv-only at the time of writing, with no confirmed peer-reviewed venue. Preprints
  are cited for *method*, never as settled fact.
- **"Not evidence for"** lines exist because the most common citation error in this literature is
  citing a paper as support for a claim it never tested.

---

## 1. Foundations: architecture and sequence models

### [S1] Attention Is All You Need

- **Title** — Attention Is All You Need
- **Authors** — Vaswani, A.; Shazeer, N.; Parmar, N.; Uszkoreit, J.; Jones, L.; Gomez, A. N.; Kaiser, Ł.; Polosukhin, I.
- **Year / venue** — 2017; NeurIPS 2017 (peer reviewed)
- **Identifier** — arXiv:1706.03762 · <https://arxiv.org/abs/1706.03762>
- **Contribution** — Introduces the Transformer: stacked self-attention plus position-wise feed-forward
  blocks, with residual connections and layer normalisation. Removes recurrence entirely, giving
  `O(T²)` attention cost but full parallelism across sequence position during training. Introduces
  scaled dot-product attention with the `1/√d_k` factor.
- **Relevance to AETHER** — The primary architectural ancestor. `ARCHITECTURE_SPEC.md` §3–§4 derive
  from it directly: multi-head attention, residual stream, position-wise MLP. The `1/√d_k` scaling is
  analysed in `NUMERICAL_STRATEGY.md` §9.6, where it is shown to make attention-logit variance `O(1)`
  at initialisation under AETHER's dimensions.
- **Limitations / assumptions** — Trained on machine translation, not language modelling. Gives no
  guidance on small-scale behaviour, on quantisation, or on CPU execution. The `O(T²)` cost is
  explicitly not solved by the paper.

### [S2] Long Short-Term Memory

- **Title** — Long Short-Term Memory
- **Authors** — Hochreiter, S.; Schmidhuber, J.
- **Year / venue** — 1997; *Neural Computation* 9(8):1735–1780 (peer reviewed)
- **Identifier** — DOI 10.1162/neco.1997.9.8.1735 · <https://doi.org/10.1162/neco.1997.9.8.1735>
- **Contribution** — Introduces the LSTM cell: an input gate, output gate, and a constant-error
  carousel that permits gradients to flow across many timesteps without vanishing. Establishes that
  gating resolves a class of vanishing-gradient failures in vanilla RNNs.
- **Relevance to AETHER** — Baseline recurrent family in `RESEARCH_SURVEY.md` §2.2. Its `O(1)`
  per-token inference cost and `O(1)` state memory are directly attractive under a 32-bit constraint,
  which is why the rejection of recurrence had to be argued rather than assumed
  (`ARCHITECTURE_SPEC.md` §10).
- **Limitations / assumptions** — Pre-dates modern optimisers, layer normalisation, and large-scale
  language modelling. Sequential training limits parallelism; the paper gives no evidence about
  training throughput on any parallel hardware.

### [S3] Learning Phrase Representations using RNN Encoder–Decoder (GRU)

- **Title** — Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation
- **Authors** — Cho, K.; van Merriënboer, B.; Gulcehre, C.; Bahdanau, D.; Bougares, F.; Schwenk, H.; Bengio, Y.
- **Year / venue** — 2014; EMNLP 2014 (peer reviewed)
- **Identifier** — arXiv:1406.1078 · <https://arxiv.org/abs/1406.1078>
- **Contribution** — Introduces the gated recurrent unit (GRU): a two-gate simplification of the LSTM
  with the update and reset gates. Fewer parameters and fewer state tensors than LSTM at comparable
  capability on the tasks studied.
- **Relevance to AETHER** — Parameter-efficiency baseline in `RESEARCH_SURVEY.md` §2.2. A GRU cell
  uses `3·d²` parameters versus an LSTM's `4·d²`, which matters at AETHER's budget where the MLP
  already dominates.
- **Limitations / assumptions** — Machine translation at small scale. The claim that GRU matches LSTM
  is task-dependent and was not systematically established.

### [S40] Deep Residual Learning

- **Title** — Deep Residual Learning for Image Recognition
- **Authors** — He, K.; Zhang, X.; Ren, S.; Sun, J.
- **Year / venue** — 2015; CVPR 2016 (peer reviewed)
- **Identifier** — arXiv:1512.03385 · <https://arxiv.org/abs/1512.03385>
- **Contribution** — Introduces identity residual connections, showing that very deep networks become
  trainable when layers learn a residual function rather than an unreferenced transformation.
  Demonstrates networks up to 152 layers and analysis at 1000 layers on CIFAR-10.
- **Relevance to AETHER** — The residual stream in `ARCHITECTURE_SPEC.md` §4 is this mechanism applied
  to sequences. Its role in AETHER is also numerical: residuals are why the identity path carries
  information unattenuated through `L = 8` layers, and why `NUMERICAL_STRATEGY.md` §9.5 has to reason
  about error growth at all rather than about signal decay.
- **Limitations / assumptions** — Computer vision, convolutional networks. Does not establish that the
  same depth behaviour holds for attention stacks; the paper predates pre-norm Transformers.

---

## 2. State-space and linear-recurrence architectures

### [S4] Structured State Space Models (S4)

- **Title** — Efficiently Modeling Long Sequences with Structured State Spaces
- **Authors** — Gu, A.; Goel, K.; Ré, C.
- **Year / venue** — 2021; ICLR 2022 (peer reviewed)
- **Identifier** — arXiv:2111.00396 · <https://arxiv.org/abs/2111.00396>
- **Contribution** — Parameterises a linear state-space model whose state-transition matrix is
  structured (diagonal-plus-low-rank), enabling both a convolution view for parallel training and a
  recurrence view for `O(1)`-per-step inference. Achieves strong results on very long sequences.
- **Relevance to AETHER** — The principal alternative family in `RESEARCH_SURVEY.md` §2.3. The
  dual train/inference view (convolve during training, recur during decoding) is precisely the
  property AETHER wants, and `ARCHITECTURE_SPEC.md` §10 records why it was not adopted at this scale.
- **Limitations / assumptions** — The evaluation is dominated by long-range arena benchmarks, not
  language modelling at small scale. Numerical conditioning of the state matrix is a known practical
  concern; the paper's discretisation assumes stable, well-conditioned dynamics.

### [S5] Mamba: selective state spaces

- **Title** — Mamba: Linear-Time Sequence Modeling with Selective State Spaces
- **Authors** — Gu, A.; Dao, T.
- **Year / venue** — 2023; **preprint** (arXiv only at time of writing)
- **Identifier** — arXiv:2312.00752 · <https://arxiv.org/abs/2312.00752>
- **Contribution** — Makes the SSM parameters input-dependent ("selective"), which breaks the
  convolution view but recovers content-based reasoning ability. Introduces a hardware-aware selective
  scan and reports linear-time scaling and competitive language-modelling results against Transformers
  of similar size.
- **Relevance to AETHER** — The strongest current argument that an `O(T)` architecture can match
  attention on language. Cited in `RESEARCH_SURVEY.md` §2.3. Critically, AETHER's
  `ARCHITECTURE_SPEC.md` §10 rejects it on a **CPU-specific** ground: the selective scan is a
  sequential dependency chain, and its reported advantage comes from GPU memory-hierarchy exploitation
  that has no 32-bit x86 analogue.
- **Limitations / assumptions** — Preprint. The headline efficiency claims are developed against GPU
  memory hierarchies. **The paper does not benchmark 32-bit x86, and AETHER must not cite it as
  evidence about CPU performance.** No throughput figure from this paper appears anywhere in the
  AETHER documentation.

### [S6] Transformers are SSMs (Mamba-2 / SSD)

- **Title** — Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality
- **Authors** — Dao, T.; Gu, A.
- **Year / venue** — 2024; ICML 2024 (peer reviewed)
- **Identifier** — arXiv:2405.21060 · <https://arxiv.org/abs/2405.21060>
- **Contribution** — Establishes a formal duality between a class of structured masked attention and
  structured state-space models, yielding a unified framework and faster algorithms for both.
- **Relevance to AETHER** — Theoretical underpinning for treating "attention vs recurrence" as a
  spectrum of masking structures rather than two unrelated families
  (`RESEARCH_SURVEY.md` §2.4). It supports AETHER's sliding-window attention being describable as a
  structured banded mask.
- **Limitations / assumptions** — The duality is exact only for specific parameterisations
  (scalar-identity state transition, specific head structure). It is a structural result, not a claim
  that any particular implementation is faster on any particular hardware.

### [S7] Griffin: gated linear recurrences with local attention

- **Title** — Griffin: Mixing Gated Linear Recurrences with Local Attention for Efficient Language Models
- **Authors** — De, S.; Smith, S. L.; Fernando, A.; Botev, A.; Cristian-Muraru, G.; Gu, A.; Haroun, R.; et al.
- **Year / venue** — 2024; **preprint**
- **Identifier** — arXiv:2402.19427 · <https://arxiv.org/abs/2402.19427>
- **Contribution** — A hybrid that interleaves gated linear recurrences with local attention, reporting
  that it matches or exceeds Transformer quality at matched parameter counts while extrapolating to
  longer sequences than seen in training.
- **Relevance to AETHER** — Direct precedent for hybrid design, and for the specific claim that
  **local** attention plus recurrence can be competitive. `ARCHITECTURE_SPEC.md` §10 Alternative B is
  a (simpler) hybrid of the same shape.
- **Limitations / assumptions** — Preprint; trained at scales far above Config M. Does not address
  32-bit execution, quantisation, or small-model regimes.

### [S8] RWKV

- **Title** — RWKV: Reinventing RNNs for the Transformer Era
- **Authors** — Peng, B.; et al.
- **Year / venue** — 2023; EMNLP 2023 Findings (peer reviewed)
- **Identifier** — arXiv:2305.13048 · <https://arxiv.org/abs/2305.13048>
- **Contribution** — A linear-attention/RNN hybrid trained in parallel and run as a recurrence,
  reporting Transformer-comparable language modelling at matched scale.
- **Relevance to AETHER** — Third linear-recurrence data point in `RESEARCH_SURVEY.md` §2.4. Cited as
  evidence the family is viable, and as a contrast to AETHER's choice of windowed attention.
- **Limitations / assumptions** — Reports no 32-bit or CPU-specific results. The recurrent formulation's
  numerical behaviour under `binary32` accumulation is not analysed in the paper.

---

## 3. Scaling, data and training

### [S9] Chinchilla — compute-optimal training

- **Title** — Training Compute-Optimal Large Language Models
- **Authors** — Hoffmann, J.; Borgeaud, S.; Mensch, A.; et al.
- **Year / venue** — 2022; NeurIPS 2022 (peer reviewed)
- **Identifier** — arXiv:2203.15556 · <https://arxiv.org/abs/2203.15556>
- **Contribution** — Refits scaling laws with a corrected methodology and concludes that parameters and
  training tokens should be scaled in roughly equal proportion, at about **20 tokens per parameter**
  for compute-optimal training — substantially more data than earlier practice used.
- **Relevance to AETHER** — The origin of the `C ≈ 6ND` convention used throughout
  [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md), and the source of the "tokens per parameter"
  axis. **AETHER deliberately trains below this ratio** (10 tokens/parameter proposed), and states
  why: under a hard compute budget, the curve is flat enough near the optimum that a smaller
  token count is a reasonable trade.
- **Limitations / assumptions** — Fitted at `10²³`–`10²⁴` FLOPs, **many orders of magnitude above
  AETHER's `10¹⁵`**. Extrapolating a fitted exponent far outside its fitted range is unsound, and
  AETHER's documents say so. The paper does not claim its ratio transfers to small models.

### [S10] TinyStories

- **Title** — TinyStories: How Small Can Language Models Be and Still Speak Coherent English?
- **Authors** — Eldan, R.; Li, Y.
- **Year / venue** — 2023; **preprint**
- **Identifier** — arXiv:2305.07759 · <https://arxiv.org/abs/2305.07759>
- **Contribution** — Shows that models with a few million parameters can produce fluent, coherent,
  grammatically well-formed English when trained on a restricted, synthetically generated corpus of
  simple stories, and that capability emerges earlier under a narrow distribution.
- **Relevance to AETHER** — **The single most important precedent for AETHER's scale.** It is cited in
  `ARCHITECTURE_SPEC.md` §8 as the reason a ~8 M-parameter model is not automatically absurd. It also
  bounds the claim: what emerges is *fluency within a narrow distribution*, not general knowledge.
- **Limitations / assumptions** — Synthetic, narrow, English-only corpus. Demonstrated capability does
  **not** extend to general knowledge, reasoning, code, or multilingual use. **Not evidence that
  Config M will acquire any general capability.**

### [S42] Deduplicating training data

- **Title** — Deduplicating Training Data Makes Language Models Better
- **Authors** — Lee, K.; Ippolito, D.; Nystrom, A.; Zhang, C.; Eck, D.; Callison-Burch, C.; Carlini, N.
- **Year / venue** — 2021; ACL 2022 (peer reviewed)
- **Identifier** — arXiv:2107.06499 · <https://arxiv.org/abs/2107.06499>
- **Contribution** — Finds near-duplicate text and long repeated substrings are pervasive in standard
  LM datasets; over 1 % of unprompted model output is verbatim training-data copy. Deduplication
  reduces memorisation roughly tenfold and reduces the train steps needed to reach a given accuracy.
  Also finds train–test overlap affects over 4 % of a standard validation set.
- **Relevance to AETHER** — Grounds the deduplication requirement in
  [`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §7 and the contamination rules in
  [`EXPERIMENTAL_METHODOLOGY.md`](EXPERIMENTAL_METHODOLOGY.md) §6. At AETHER's data scale, a repeated
  passage can consume a non-trivial fraction of the entire budget.
- **Limitations / assumptions** — English web corpora. The specific 1 % and 4 % figures are
  dataset-dependent and **must not be quoted as AETHER properties**.

### [S41] SGDR — cosine annealing

- **Title** — SGDR: Stochastic Gradient Descent with Warm Restarts
- **Authors** — Loshchilov, I.; Hutter, F.
- **Year / venue** — 2016; ICLR 2017 (peer reviewed)
- **Identifier** — arXiv:1608.03983 · <https://arxiv.org/abs/1608.03983>
- **Contribution** — Introduces cosine annealing of the learning rate with warm restarts, improving
  anytime performance over fixed or step schedules on the benchmarks studied.
- **Relevance to AETHER** — Source of the cosine-decay schedule proposed in
  `ARCHITECTURE_SPEC.md` §8A.3. AETHER proposes cosine decay **without** restarts, because a single
  monotone run is simpler to make resumable ([`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §6).
- **Limitations / assumptions** — Image classification and a downsampled ImageNet, not language
  modelling. The restart benefit is not established for AETHER's setting, which is why AETHER does
  not use restarts.

### [S20] Adam

- **Title** — Adam: A Method for Stochastic Optimization
- **Authors** — Kingma, D. P.; Ba, J.
- **Year / venue** — 2014; ICLR 2015 (peer reviewed)
- **Identifier** — arXiv:1412.6980 · <https://arxiv.org/abs/1412.6980>
- **Contribution** — Introduces Adam, combining momentum with per-parameter second-moment scaling.
  Requires two additional state tensors per parameter.
- **Relevance to AETHER** — The optimiser family. Its **memory cost is the reason**
  [`MEMORY_BUDGET.md`](MEMORY_BUDGET.md) §6 fixes training state at 16 bytes/parameter and why
  activation checkpointing becomes mandatory at Config M.
- **Limitations / assumptions** — The paper's convergence analysis has known gaps for the general
  non-convex case. Not a language-modelling paper.

### [S28] AdamW

- **Title** — Decoupled Weight Decay Regularization
- **Authors** — Loshchilov, I.; Hutter, F.
- **Year / venue** — 2017; ICLR 2019 (peer reviewed)
- **Identifier** — arXiv:1711.05101 · <https://arxiv.org/abs/1711.05101>
- **Contribution** — Shows L2 regularisation and weight decay are **not equivalent** for adaptive
  optimisers, and that decoupling decay from the gradient-based update improves generalisation.
- **Relevance to AETHER** — `ARCHITECTURE_SPEC.md` §8A.3 specifies AdamW, not Adam-with-L2. This is a
  correctness point, not a preference: the coupled form would route decay through the second-moment
  estimate and produce a different effective schedule.
- **Limitations / assumptions** — Image classification and language modelling at moderate scale. Does
  not determine the optimal decay coefficient, which AETHER leaves `[OPEN]`.

### [S39] Knowledge distillation

- **Title** — Distilling the Knowledge in a Neural Network
- **Authors** — Hinton, G.; Vinyals, O.; Dean, J.
- **Year / venue** — 2015; NIPS 2014 Deep Learning Workshop (workshop, lightly reviewed)
- **Identifier** — arXiv:1503.02531 · <https://arxiv.org/abs/1503.02531>
- **Contribution** — Introduces temperature-scaled soft-target distillation, compressing an ensemble's
  behaviour into a single model.
- **Relevance to AETHER** — Relevant **only** to the bounded form of distillation AETHER permits:
  distilling from *research-generated supervision* into AETHER's own randomly initialised model.
  `INTELLIGENCE_DENSITY_RESEARCH.md` §6 states the boundary — AETHER must not initialise from, or
  adopt the weights or representations of, another model, which is why full model-distillation is
  **out of scope**, not merely unimplemented.
- **Limitations / assumptions** — Assumes a teacher model exists with the desired behaviour. Says
  nothing about training from random initialisation without a teacher.

---

## 3A. Tokenisation

`[S11]`–`[S14]` were cited throughout [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) and
[`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) but were **not present in this registry** until the Phase 2
citation audit found the gap. They are annotated here in full. All four were verified to exist at the stated
identifiers during that audit.

### [S11] Neural Machine Translation of Rare Words with Subword Units

- **Title** — Neural Machine Translation of Rare Words with Subword Units
- **Authors** — Sennrich, R.; Haddow, B.; Birch, A.
- **Year / venue** — 2015 (arXiv v1); **ACL 2016** (peer reviewed)
- **Identifier** — arXiv:1508.07909 · <https://arxiv.org/abs/1508.07909>
- **Contribution** — Introduces byte-pair-encoding (BPE) segmentation for NMT, encoding rare and
  out-of-vocabulary words as sequences of subword units. Reports +1.1 BLEU (En–De) and +1.3 BLEU
  (En–Ru) on WMT 15 over a back-off dictionary baseline. Also compares character n-gram models
  against BPE segmentation.
- **Relevance to AETHER** — The origin of the BPE algorithm that `TOKENIZER_SPEC.md` adopts. AETHER's
  merge-count scheduling and the 8,160-merge budget derive from this algorithm, not from this paper's
  results.
- **Limitations / assumptions** — Evaluated on **machine translation**, not language modelling, and on
  word-level pre-tokenised input. Does **not** establish that BPE is optimal for small-vocabulary
  language modelling, nor anything about a 2048-vocabulary character regime. **Not evidence** for any
  claim about tokenizer efficiency at `V = 8192`.

### [S12] Subword Regularization

- **Title** — Subword Regularization: Improving Neural Network Translation Models with Multiple
  Subword Candidates
- **Authors** — Kudo, T.
- **Year / venue** — 2018; **ACL 2018** (peer reviewed, long paper)
- **Identifier** — arXiv:1804.10959 · <https://arxiv.org/abs/1804.10959>
- **Contribution** — Proposes subword regularisation: sampling among multiple subword segmentations
  during training as a noise source. Introduces the **unigram language model** segmentation algorithm,
  which assigns probabilities to subword sequences and supports sampling over candidate segmentations.
- **Relevance to AETHER** — The unigram algorithm is the alternative to BPE considered in
  [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) and rejected for AETHER on complexity grounds. The
  sampling method is **not** adopted: AETHER requires deterministic encoding for reproducibility.
- **Limitations / assumptions** — Gains are reported mainly on **low-resource and out-of-domain**
  settings. Does not compare unigram against BPE at small vocabulary sizes. **Not evidence** that
  unigram is better than BPE for AETHER's regime, only that it is a viable alternative.

### [S13] SentencePiece

- **Title** — SentencePiece: A simple and language independent subword tokenizer and detokenizer for
  Neural Text Processing
- **Authors** — Kudo, T.; Richardson, J.
- **Year / venue** — 2018; **EMNLP 2018 demo track** (peer reviewed, demo paper)
- **Identifier** — arXiv:1808.06226 · <https://arxiv.org/abs/1808.06226>
- **Contribution** — Describes SentencePiece, a language-independent subword tokenizer that trains
  directly on raw sentences without pre-tokenisation, implementing both BPE and unigram models. Reports
  NMT accuracy comparable to conventional pre-tokenised subword training on En–Ja.
- **Relevance to AETHER** — Cited as the reference implementation that establishes lossless
  detokenisation and whitespace-as-a-token handling, which `TOKENIZER_SPEC.md` requires. AETHER does
  **not** depend on SentencePiece; the interface contract is what is borrowed.
- **Limitations / assumptions** — A **demo paper**; the depth of empirical validation is correspondingly
  limited. Evaluated on NMT.

### [S14] GPT-2 (byte-level BPE)

- **Title** — Language Models are Unsupervised Multitask Learners
- **Authors** — Radford, A.; Wu, J.; Child, R.; Luan, D.; Amodei, D.; Sutskever, I.
- **Year / venue** — 2019; **OpenAI technical report** (not peer reviewed)
- **Identifier** — no arXiv identifier; OpenAI technical report. Byte-level BPE with a 50,257-token
  vocabulary.
- **Contribution** — Popularises byte-level BPE, in which the base vocabulary is the 256 byte values so
  that no input is ever out-of-vocabulary. Demonstrates zero-shot transfer across tasks at scale.
- **Relevance to AETHER** — The direct precedent for AETHER's byte-level BPE with `V = 8192`. The
  byte-initialisation property — every input encodable, never `UNK` — is the guarantee
  `TOKENIZER_SPEC.md` §2 relies on.
- **Limitations / assumptions** — A **technical report**, not peer reviewed. Uses `V = 50,257`, roughly
  6× AETHER's vocabulary, so its compression ratios do **not** transfer. **Not evidence** about the
  quality of a byte-level model at `V = 8192`.

---

## 3B. Quantisation

`[S15]`–`[S19]` were likewise cited without registry entries. All five were verified during the same
audit. **None of them is evidence for AETHER's specific numerical claims** — they are cited as the
literature that motivates quantisation as a direction, and [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md)
§9A explicitly derives AETHER's own error figures by simulation rather than quoting any of these.

### [S15] LLM.int8()

- **Title** — LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale
- **Authors** — Dettmers, T.; Lewis, M.; Belkada, Y.; Zettlemoyer, L.
- **Year / venue** — 2022; **NeurIPS 2022** (peer reviewed)
- **Identifier** — arXiv:2208.07339 · <https://arxiv.org/abs/2208.07339>
- **Contribution** — Int8 matrix multiplication for transformer projection layers, halving inference
  memory while retaining full-precision performance. Identifies **systematic emergent outlier features**
  and handles them with vector-wise quantisation plus a mixed-precision decomposition that keeps outlier
  dimensions in 16-bit while >99.9% of values multiply in 8-bit. Demonstrated to 175B parameters.
- **Relevance to AETHER** — The outlier-feature problem is the direct reason
  [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9A does **not** propose activation quantisation
  initially: AETHER cannot rely on emergent outlier features existing in an 8.4M-parameter model, and
  the paper gives no basis for assuming they do.
- **Limitations / assumptions** — Requires **native int8 dot products** and mixed-precision kernels; a
  32-bit x87 CPU has neither. All experiments are on GPU, on models ≥125M parameters — **three orders of
  magnitude above Config M**. Outliers emerge at scale; whether they exist at 8.4M is **unestablished**.

### [S16] GPTQ

- **Title** — GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers
- **Authors** — Frantar, E.; Ashkboos, S.; Hoefler, T.; Alistarh, D.
- **Year / venue** — 2022 arXiv; **ICLR 2023** (peer reviewed)
- **Identifier** — arXiv:2210.17323 · <https://arxiv.org/abs/2210.17323>
- **Contribution** — One-shot weight quantisation using approximate second-order (Hessian)
  information, to 3–4 bits with negligible accuracy loss on models up to 175B. Reports reasonable
  accuracy at 2-bit and ternary.
- **Relevance to AETHER** — Cited as the class of **post-training** methods AETHER does not adopt in
  Phase 8: they require a calibration set and a Hessian approximation, both of which are disproportionate
  to an 8.4M-parameter model, and neither addresses AETHER's arithmetic constraint.
- **Limitations / assumptions** — Needs calibration data and per-layer Hessian estimates. The reported
  speedups (3.25× on A100, 4.5× on A6000) are **GPU kernel results and must not be quoted for AETHER**;
  [`RESEARCH_PRINCIPLES.md`](RESEARCH_PRINCIPLES.md) §7 forbids exactly this comparison.

### [S17] SmoothQuant

- **Title** — SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models
- **Authors** — Xiao, G.; Lin, J.; Seznec, M.; Wu, H.; Demouth, J.; Han, S.
- **Year / venue** — 2022 arXiv; **ICML 2023** (peer reviewed)
- **Identifier** — arXiv:2211.10438 · <https://arxiv.org/abs/2211.10438>
- **Contribution** — Training-free W8A8 quantisation that migrates quantisation difficulty from
  activations to weights via a **mathematically equivalent** per-channel rescaling, exploiting the
  observation that weights are easier to quantise than activations. Reports up to 1.56× speedup and 2×
  memory reduction.
- **Relevance to AETHER** — The migration trick is the specific mechanism
  [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9A notes is **inapplicable** to AETHER: it is
  designed to enable int8 *activation* kernels, which AETHER has no way to execute without native int8
  support.
- **Limitations / assumptions** — Requires activation statistics collected offline, and assumes the
  target hardware has efficient int8 GEMM. **Not evidence** that the trick helps on scalar x87.

### [S18] AWQ

- **Title** — AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration
- **Authors** — Lin, J.; Tang, J.; Tang, H.; Yang, S.; Chen, W.-M.; Wang, W.-C.; Xiao, G.; Dang, X.;
  Gan, C.; Han, S.
- **Year / venue** — 2023 arXiv; **MLSys 2024** (peer reviewed, **Best Paper Award**)
- **Identifier** — arXiv:2306.00978 · <https://arxiv.org/abs/2306.00978>
- **Contribution** — Weight-only low-bit quantisation that identifies salient weight channels from
  **activation** statistics rather than weight magnitudes, protecting ~1% of channels by an equivalent
  scaling transform. Requires no backpropagation or reconstruction, so it generalises to domains absent
  from the calibration set.
- **Relevance to AETHER** — Motivates the observation recorded in
  [`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md) and
  [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) §9A: **salience is a property of activations, and
  AETHER has none until a model is trained.** The per-channel int8 simulation found no benefit over
  per-tensor under Gaussian initialisation for exactly this reason.
- **Limitations / assumptions** — Still requires a calibration set. Reported >3× speedups are GPU
  results. **Not evidence** that per-channel scaling helps an untrained model.

### [S19] BitNet b1.58

- **Title** — The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits
- **Authors** — Ma, S.; Wang, H.; Ma, L.; Wang, L.; Wang, W.; Huang, S.; Dong, L.; Wang, R.; Xue, J.;
  Wei, F.
- **Year / venue** — 2024; **arXiv preprint, "work in progress"** — **not peer reviewed**
- **Identifier** — arXiv:2402.17764 · <https://arxiv.org/abs/2402.17764>
- **Contribution** — Describes **BitNet b1.58**, a *from-scratch* training scheme in which every weight
  is ternary `{-1, 0, 1}`. Reports matching full-precision transformers of the same size and token
  budget on perplexity and end-task performance, with lower latency, memory, throughput and energy cost.
  Proposes a new scaling recipe for 1.58-bit training.
- **Relevance to AETHER** — The only cited method that is **from-scratch rather than post-training**,
  and therefore the only one structurally compatible with AETHER's constraint of training its own model.
  It is recorded in [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) as a considered direction and **not
  adopted**: ternary weights would forego the fp32 numerics
  [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md) analyses, and the paper's evidence is entirely at
  scale ≥700M parameters.
- **Limitations / assumptions** — **Preprint explicitly labelled work in progress; treat as unrefereed.**
  All reported results are far above AETHER's scale. **Not evidence** that ternary weights train
  successfully at 8.4M parameters or on 32-bit hardware without native ternary support.

---

## 4. Normalisation

### [S21] Layer Normalization

- **Title** — Layer Normalization
- **Authors** — Ba, J. L.; Kiros, J. R.; Hinton, G. E.
- **Year / venue** — 2016; **preprint** (widely cited, no confirmed peer-reviewed venue)
- **Identifier** — arXiv:1607.06450 · <https://arxiv.org/abs/1607.06450>
- **Contribution** — Normalises across features within a single example, rather than across a batch,
  removing batch-size dependence and improving training stability for recurrent networks.
- **Relevance to AETHER** — Baseline normalisation. AETHER uses RMSNorm `[S22]` instead, and
  `ARCHITECTURE_SPEC.md` §4.7 states the reason: no mean subtraction means no mean reduction, which
  halves the reduction work and removes one accumulator.
- **Limitations / assumptions** — Preprint. Demonstrated largely on recurrent and convolutional
  models; its behaviour inside modern pre-norm Transformers was characterised later by `[S27]`.

### [S22] RMSNorm

- **Title** — Root Mean Square Layer Normalization
- **Authors** — Zhang, B.; Sennrich, R.
- **Year / venue** — 2019; NeurIPS 2019 (peer reviewed)
- **Identifier** — arXiv:1910.07467 · <https://arxiv.org/abs/1910.07467>
- **Contribution** — Proposes normalising by root-mean-square only, dropping mean-centering and the
  bias term, and reports comparable or better accuracy at reduced computation.
- **Relevance to AETHER** — The normalisation AETHER adopts (`ARCHITECTURE_SPEC.md` §4.7). The saving
  is concrete and counts twice: one fewer reduction pass in the forward kernel, and one fewer term in
  the backward pass (`NUMERICAL_STRATEGY.md` §4.2).
- **Limitations / assumptions** — Translation and moderate-scale language modelling. The
  "comparable accuracy" claim is empirical and scale-dependent, not a theorem.

### [S27] On Layer Normalization in the Transformer Architecture

- **Title** — On Layer Normalization in the Transformer Architecture
- **Authors** — Xiong, R.; Yang, Y.; He, D.; Zheng, K.; Zheng, S.; Xing, C.; Zhang, H.; Lan, Y.; Wang, L.; Liu, T.-Y.
- **Year / venue** — 2020; ICML 2020 (peer reviewed)
- **Identifier** — arXiv:2002.04745 · <https://arxiv.org/abs/2002.04745>
- **Contribution** — Shows theoretically and empirically that **post-norm** Transformers have
  initialisation-time gradients whose magnitude is large and independent of depth, making learning-rate
  warm-up essential; **pre-norm** gradients are well-behaved, so warm-up can be removed. Reports pre-norm
  BERT reaching a target at 500k steps versus 700k for post-norm.
- **Relevance to AETHER** — Direct justification for pre-norm placement
  (`ARCHITECTURE_SPEC.md` §8A.2) **and** for omitting warm-up. On a machine where a run costs days,
  removing a warm-up phase that has been shown unnecessary is a real saving.
- **Limitations / assumptions** — BERT-scale encoder experiments. AETHER applies the result at
  `d=256, L=8`, far outside the studied scale; `ARCHITECTURE_SPEC.md` §8A.2 marks this `[ASSUMPTION]`.

---

## 5. Attention variants and efficiency

### [S32] Multi-query attention

- **Title** — Fast Transformer Decoding: One Write-Head is All You Need
- **Authors** — Shazeer, N.
- **Year / venue** — 2019; **preprint**
- **Identifier** — arXiv:1911.02150 · <https://arxiv.org/abs/1911.02150>
- **Contribution** — Shares a single key and value head across all query heads, drastically reducing
  the memory bandwidth required to reload K/V tensors during incremental decoding, with only minor
  quality degradation.
- **Relevance to AETHER** — AETHER uses `H = 8` query heads and `H_kv = 8` key/value heads (i.e. **not**
  MQA). The paper is cited in `RESEARCH_SURVEY.md` §2.1 and `ARCHITECTURE_SPEC.md` §10 to explain why
  MQA was **declined**: AETHER's KV cache is already tiny at `d_h = 32`, so the bandwidth saving is
  small, while the quality cost is not quantified at AETHER's scale.
- **Limitations / assumptions** — Preprint. Quality degradation is described as "minor" without a
  systematic small-scale characterisation.

### [S33] Grouped-query attention

- **Title** — GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints
- **Authors** — Ainslie, J.; Lee-Thorp, J.; de Jong, M.; Zemlyanskiy, Y.; Lebrón, F.; Sanghai, S.
- **Year / venue** — 2023; EMNLP 2023 (peer reviewed)
- **Identifier** — arXiv:2305.13245 · <https://arxiv.org/abs/2305.13245>
- **Contribution** — Generalises MQA to an intermediate number of key/value heads, reporting quality
  close to multi-head attention at speed comparable to MQA, plus an uptraining recipe.
- **Relevance to AETHER** — The natural middle option. `ARCHITECTURE_SPEC.md` §10 notes GQA is a
  **one-field change** in the proposed format (`n_kv_heads`), so it remains a live option that can be
  adopted later without breaking the container specification.
- **Limitations / assumptions** — Not evaluated at small scale or on CPU; the speed claims are GPU-oriented.

### [S24] RoPE — rotary position embedding

- **Title** — RoFormer: Enhanced Transformer with Rotary Position Embedding
- **Authors** — Su, J.; Lu, Y.; Pan, S.; Murtadha, A.; Wen, B.; Liu, Y.
- **Year / venue** — 2021; Neurocomputing 2024 (peer reviewed); **long a preprint**
- **Identifier** — arXiv:2104.09864 · <https://arxiv.org/abs/2104.09864>
- **Contribution** — Encodes position by rotating query and key vectors in disjoint 2-D subspaces,
  making attention scores depend on relative offset and decaying with distance.
- **Relevance to AETHER** — The position scheme in `ARCHITECTURE_SPEC.md` §4.3. Chosen over learned
  absolute embeddings because it adds **zero parameters** and improves numerical range behaviour at
  long context (`NUMERICAL_STRATEGY.md` §5.4).
- **Limitations / assumptions** — The paper's long-context extrapolation claims are task-specific and
  depend on the base frequency `Θ`. AETHER sets `Θ = 10000` without a fitted sweep, marked `[OPEN]`.

### [S23] GELU

- **Title** — Gaussian Error Linear Units (GELUs)
- **Authors** — Hendrycks, D.; Gimpel, K.
- **Year / venue** — 2016; **preprint**
- **Identifier** — arXiv:1606.08415 · <https://arxiv.org/abs/1606.08415>
- **Contribution** — Proposes the GELU activation, weighting inputs by their Gaussian cumulative
  distribution.
- **Relevance to AETHER** — AETHER uses **SiLU/Swish** in the SwiGLU gate rather than GELU, because
  SiLU needs only a sigmoid (`1/(1+e^-x)`) while GELU's exact form needs `erf`. On a 32-bit target
  where transcendental functions are library calls, that difference is measurable.
  `ARCHITECTURE_SPEC.md` §4.4 records the choice.
- **Limitations / assumptions** — Preprint. Gives no numerical or embedded-systems analysis.

---

## 6. Adaptive and conditional computation

### [S29] Adaptive Computation Time (ACT)

- **Title** — Adaptive Computation Time for Recurrent Neural Networks
- **Authors** — Graves, A.
- **Year / venue** — 2016; **preprint**
- **Identifier** — arXiv:1603.08983 · <https://arxiv.org/abs/1603.08983>
- **Contribution** — Introduces ACT: a differentiable halting mechanism that lets a recurrent network
  learn how many computational steps to take per input, with a ponder cost penalising computation.
  Shows large gains on synthetic algorithmic tasks (parity, logic, addition, sorting).
  **Critically**, on character-level language modelling the paper reports ACT does **not** yield large
  performance gains.
- **Relevance to AETHER** — The origin of the adaptive-computation family, cited in
  [`ADAPTIVE_COMPUTATION.md`](ADAPTIVE_COMPUTATION.md) §2. That document leans heavily on the paper's
  *negative* language-modelling result: it is the best available evidence that adaptive depth is not a
  free win for AETHER's workload, and it is why AETHER proposes an **external controller** rather than
  learned halting.
- **Limitations / assumptions** — Preprint. Evaluated on RNNs on small synthetic tasks; never applied
  to a modern small Transformer. The ponder cost requires tuning a coefficient with no principled
  setting.

### [S30] PonderNet

- **Title** — PonderNet: Learning to Ponder
- **Authors** — Banino, A.; Balaguer, J.; Blundell, C.
- **Year / venue** — 2021; ICML 2021 AutoML Workshop (workshop)
- **Identifier** — arXiv:2107.05407 · <https://arxiv.org/abs/2107.05407>
- **Contribution** — Reformulates adaptive computation as a probabilistic halting distribution trained
  by maximum likelihood, reporting better performance than prior adaptive methods on a synthetic
  problem, extrapolation where fixed-depth models fail, and matched SOTA on a QA dataset using less
  compute.
- **Relevance to AETHER** — The improved alternative to ACT (`ADAPTIVE_COMPUTATION.md` §2). AETHER
  cites it as the strongest learned-halting method and still declines to adopt it in Phase 2, because
  its benefit is demonstrated on synthetic reasoning tasks rather than on small language models.
- **Limitations / assumptions** — Workshop paper. Its headline gains are on tasks constructed to
  reward variable computation; transfer to open-ended generation is unestablished.

### [S31] Sparsely-gated mixture of experts

- **Title** — Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer
- **Authors** — Shazeer, N.; Mirhoseini, A.; Maziarz, K.; Davis, A.; Le, Q.; Hinton, G.; Dean, J.
- **Year / venue** — 2017; ICLR 2017 (peer reviewed)
- **Identifier** — arXiv:1701.06538 · <https://arxiv.org/abs/1701.06538>
- **Contribution** — Introduces a sparsely-gated MoE layer with up to thousands of feed-forward
  experts, where a trainable gate selects a sparse subset per example, increasing capacity without
  proportional compute. Applies it between stacked LSTM layers, reaching up to 137 B parameters.
- **Relevance to AETHER** — `ARCHITECTURE_SPEC.md` §10 and `ADAPTIVE_COMPUTATION.md` §4 reject MoE on a
  **memory** ground, not a compute one: sparsity saves FLOPs but every expert's weights must still be
  resident or paged, and at a 512 MiB working target the resident footprint is the binding constraint.
  This is the clearest example in Phase 2 of an optimisation that helps the wrong resource.
- **Limitations / assumptions** — Distributed GPU clusters. Expert load balancing is a known difficulty
  the paper addresses only partially. No CPU or memory-constrained analysis.

### [S34] Chain-of-thought prompting

- **Title** — Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
- **Authors** — Wei, J.; Wang, X.; Schuurmans, D.; Bosma, M.; Ichter, B.; Xia, F.; Chi, E.; Le, Q.; Zhou, D.
- **Year / venue** — 2022; NeurIPS 2022 (peer reviewed)
- **Identifier** — arXiv:2201.11903 · <https://arxiv.org/abs/2201.11903>
- **Contribution** — Shows that eliciting intermediate reasoning steps in few-shot prompts substantially
  improves performance on arithmetic, commonsense and symbolic reasoning — **but the effect emerges
  only in sufficiently large models**, with gains demonstrated on models up to 540 B parameters.
- **Relevance to AETHER** — Cited in `ADAPTIVE_COMPUTATION.md` §3 as the reason AETHER does **not**
  propose a chain-of-thought capability for Config M. The paper's own framing — that the ability
  "emerges naturally in sufficiently large language models" — is the least convenient result in this
  entire reference list for a project of AETHER's scale.
- **Limitations / assumptions** — Prompting only; no training. Emergence thresholds are model- and
  task-dependent. **Not evidence that a small model can be prompted into multi-step reasoning.**

---

### [S49] Multi-token prediction

- **Title** — Better & Faster Large Language Models via Multi-token Prediction
- **Authors** — Gloeckle, F.; Idrissi, B. Y.; Rozière, B.; Lopez-Paz, D.; Synnaeve, G.
- **Year / venue** — 2024; ICML 2024 (peer reviewed)
- **Identifier** — arXiv:2404.19737 · <https://arxiv.org/abs/2404.19737>
- **Contribution** — Trains a model to predict several future tokens at each position via independent
  output heads, reporting improved sample efficiency and faster inference on some workloads.
- **Relevance to AETHER** — `TRAINING_STRATEGY.md` §3.2 defers it to Phase 8. The extra heads multiply
  the parameter count of the output layer, which is already the largest single reduce in Config M
  (`NUMERICAL_STRATEGY.md` §9.2), so the memory and numerics cost must be assessed before adoption.
- **Limitations / assumptions** — Trained at 7 B parameters. Adds output heads and therefore parameters,
  which is the opposite of what a parameter-tight budget wants. **Not evidence of benefit at 8 M.**

---

### [S50] Tensor Programs V — μP and zero-shot hyperparameter transfer

- **Title** — Tensor Programs V: Tuning Large Neural Networks via Zero-Shot Hyperparameter Transfer
- **Authors** — Yang, G.; Hu, E. J.; Babuschkin, I.; Sidor, S.; Liu, X.; Farhi, D.; Ryder, N.; Pachocki, J.; Chen, W.; Gao, J.
- **Year / venue** — 2022; NeurIPS 2021 (peer reviewed)
- **Identifier** — arXiv:2203.03466 · <https://arxiv.org/abs/2203.03466>
- **Contribution** — Shows that in the Maximal Update Parametrisation (μP) many optimal hyperparameters
  remain stable as model size changes, enabling tuning on a small proxy and zero-shot transfer to a large
  target. Demonstrates transfer from 13 M → 350 M (matching BERT-large) and 40 M → 6.7 B (matching GPT-3),
  with tuning cost a small fraction of pretraining.
- **Relevance to AETHER** — Directly addresses the project's most consequential unexamined assumption:
  `ARCHITECTURE_SPEC.md` §8A.3 transfers a learning rate tuned on Config T to Config M without verification.
  Under the standard parameterisation that transfer is biased by `√(width ratio)`; under μP it is justified.
  See [`OPTIMISATION_THEORY.md`](OPTIMISATION_THEORY.md) §3.
- **Limitations / assumptions** — Proven in the infinite-width limit; finite-width deviation is unquantified.
  All validated transfers go **upward from 13 M parameters**, whereas AETHER would transfer upward from
  0.23 M — below every validated point. Says nothing about data-limited regimes.

### [S51] Scaling Laws for Neural Language Models

- **Title** — Scaling Laws for Neural Language Models
- **Authors** — Kaplan, J.; McCandlish, S.; Henighan, T.; Brown, T. B.; Chess, B.; Child, R.; Gray, S.; Radford, A.; Wu, J.; Amodei, D.
- **Year / venue** — 2020; **preprint**
- **Identifier** — arXiv:2001.08361 · <https://arxiv.org/abs/2001.08361>
- **Contribution** — Establishes that language-model cross-entropy loss follows power laws in model size,
  dataset size and training compute across more than seven orders of magnitude, and that architectural details
  such as width and depth have minimal effect within a wide range. Derives compute-optimal allocation.
- **Relevance to AETHER** — The origin of the `6ND` compute convention used throughout
  [`TRAINING_FEASIBILITY.md`](TRAINING_FEASIBILITY.md) and derived from first principles in
  [`MATHEMATICAL_FOUNDATIONS.md`](MATHEMATICAL_FOUNDATIONS.md) §5. Also the source of the claim that
  **architecture matters less than scale** — which is directly inconvenient for a project whose identity is
  architectural, and is cited as such in [`INTELLIGENCE_DENSITY_RESEARCH.md`](INTELLIGENCE_DENSITY_RESEARCH.md) §4.
- **Limitations / assumptions** — Preprint; the exponent estimates were later revised by `[S9]` (Chinchilla),
  which found the parameter/token allocation was different. Fitted far above AETHER's scale. **The
  "architecture doesn't matter much" finding is a statement about width and depth, not about family** — it
  does not license the conclusion that attention and recurrence are interchangeable.

---

## 7. Retrieval and knowledge access

### [S38] BM25 and the probabilistic relevance framework

- **Title** — The Probabilistic Relevance Framework: BM25 and Beyond
- **Authors** — Robertson, S.; Zaragoza, H.
- **Year / venue** — 2009; *Foundations and Trends in Information Retrieval* 3(4):333–389 (peer reviewed)
- **Identifier** — DOI 10.1561/1500000019 · <https://doi.org/10.1561/1500000019>
- **Contribution** — The definitive treatment of the probabilistic relevance framework, deriving BM25
  and BM25F from explicit modelling assumptions, with discussion of parameter optimisation.
- **Relevance to AETHER** — The retrieval baseline in [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) §4.
  BM25 needs only an inverted index — no embedding model, no vector store — which makes it the only
  retrieval method AETHER can run **inside the 512 MiB working target without a second neural network**.
- **Limitations / assumptions** — Term-matching: BM25 cannot retrieve a document sharing no surface
  term with the query. Holds for English-centric tokenisation; behaviour on Urdu/Hindi depends on
  tokenisation and stemming choices the paper does not address.

### [S36] Dense passage retrieval

- **Title** — Dense Passage Retrieval for Open-Domain Question Answering
- **Authors** — Karpukhin, V.; Oğuz, B.; Min, S.; Lewis, P.; Wu, L.; Edunov, S.; Chen, D.; Yih, W.
- **Year / venue** — 2020; EMNLP 2020 (peer reviewed)
- **Identifier** — arXiv:2004.04906 · <https://arxiv.org/abs/2004.04906>
- **Contribution** — Shows a dual-encoder dense retriever can be trained from a small number of
  question–passage pairs and **outperforms a strong Lucene-BM25 system by 9–19 points absolute** in
  top-20 passage retrieval accuracy across open-domain QA datasets.
- **Relevance to AETHER** — The strongest evidence *against* AETHER's retrieval choice, and cited as
  such in `KNOWLEDGE_SYSTEM_SPEC.md` §4. AETHER does not dismiss it; it observes that the DPR result
  requires a **second trained neural encoder** whose parameters and inference cost are not in AETHER's
  memory budget, and marks hybrid retrieval as the intended Phase 10 direction.
- **Limitations / assumptions** — Assumes a trained dual encoder. The comparison is at a scale and on
  a corpus very different from AETHER's offline collections.

### [S37] Retrieval-augmented generation

- **Title** — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- **Authors** — Lewis, P.; Perez, E.; Piktus, A.; Petroni, F.; Karpukhin, V.; Goyal, N.; Küttler, H.; Lewis, M.; Yih, W.; Rocktäschel, T.; Riedel, S.; Kiela, D.
- **Year / venue** — 2020; NeurIPS 2020 (peer reviewed)
- **Identifier** — arXiv:2005.11401 · <https://arxiv.org/abs/2005.11401>
- **Contribution** — Combines a parametric seq2seq model with a non-parametric dense index of
  Wikipedia, showing that separating knowledge from parameters improves specificity and factual
  accuracy and gives a route to provenance and knowledge updating.
- **Relevance to AETHER** — The core rationale for [`KNOWLEDGE_SYSTEM_SPEC.md`](KNOWLEDGE_SYSTEM_SPEC.md) and for
  AETHER's component separation: a small Core should not be asked to store world knowledge in
  parameters. RAG's motivation — "providing provenance and updating world knowledge remain open
  research problems" — is exactly AETHER's problem, at 1/20 000th the parameter count.
- **Limitations / assumptions** — Requires a pre-trained retriever and generator. AETHER adopts the
  *architecture of the idea* without the pre-trained components, which is a materially harder setting
  the paper does not study.

---

## 8. Evaluation

### [S43] MMLU

- **Title** — Measuring Massive Multitask Language Understanding
- **Authors** — Hendrycks, D.; Burns, C.; Basart, S.; Zou, A.; Mazeika, M.; Song, D.; Steinhardt, J.
- **Year / venue** — 2020; ICLR 2021 (peer reviewed)
- **Identifier** — arXiv:2009.03300 · <https://arxiv.org/abs/2009.03300>
- **Contribution** — A 57-subject multiple-choice benchmark for multitask knowledge and reasoning.
  Reports that most contemporary models were near random chance, and that even the largest GPT-3
  improved over chance by only about 20 points on average.
- **Relevance to AETHER** — Appears in [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §2 as a benchmark
  AETHER **explicitly expects to score near chance on**, and therefore must not report as a headline.
  Citing the near-chance baselines is what makes that expectation falsifiable rather than rhetorical.
- **Limitations / assumptions** — Knowledge-heavy; heavily contaminated in modern practice. Contamination
  is precisely why AETHER's evaluation rules forbid tuning on it.

### [S44] ARC

- **Title** — Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge
- **Authors** — Clark, P.; Cowhey, I.; Etzioni, O.; Khot, T.; Sabharwal, A.; Schoenick, C.; Tafjord, O.
- **Year / venue** — 2018; **preprint** (dataset paper)
- **Identifier** — arXiv:1803.05457 · <https://arxiv.org/abs/1803.05457>
- **Contribution** — A grade-school science QA set split into Easy and Challenge portions, where the
  Challenge set contains only questions that both a retrieval baseline and a word-co-occurrence
  baseline answered incorrectly. Reports that leading neural models of the time failed to beat random
  on the Challenge set.
- **Relevance to AETHER** — Used in `EVALUATION_PLAN.md` §2 as a **reasoning** probe with a documented
  random baseline, which is what makes a near-random score interpretable rather than merely
  disappointing.
- **Limitations / assumptions** — English, grade-school science. Small (7,787 questions), so per-subset
  scores carry wide confidence intervals.

### [S48] Deep ensembles for uncertainty

- **Title** — Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles
- **Authors** — Lakshminarayanan, B.; Pritzel, A.; Blundell, C.
- **Year / venue** — 2016; NIPS 2017 (peer reviewed)
- **Identifier** — arXiv:1612.01474 · <https://arxiv.org/abs/1612.01474>
- **Contribution** — Shows a small ensemble of independently initialised networks yields well-calibrated
  predictive uncertainty comparable to approximate Bayesian methods, with little tuning, and expresses
  higher uncertainty out of distribution.
- **Relevance to AETHER** — The reference point for `ADAPTIVE_COMPUTATION.md` §5's confidence
  discussion. AETHER **cannot afford an ensemble** — `k` copies multiply both storage and compute by
  `k` — and this paper is cited to make that cost explicit rather than to imply AETHER has calibrated
  uncertainty. It does not.
- **Limitations / assumptions** — Classification and regression benchmarks. Nothing about
  autoregressive token-level uncertainty, which is what an adaptive controller would actually need.

### [S45] T5 — the text-to-text framing and systematic ablation

- **Title** — Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer
- **Authors** — Raffel, C.; Shazeer, N.; Roberts, A.; Lee, K.; Narang, S.; Matena, M.; Zhou, Y.; Li, W.; Liu, P. J.
- **Year / venue** — 2019; *JMLR* 21 (2020) (peer reviewed)
- **Identifier** — arXiv:1910.10683 · <https://arxiv.org/abs/1910.10683>
- **Contribution** — Casts every NLP task as text-to-text and performs a large systematic ablation over
  architectures, objectives, datasets and scale. Notably compares pre-training objectives including
  span-corruption and prefix-LM-style objectives.
- **Relevance to AETHER** — Cited in [`TRAINING_STRATEGY.md`](TRAINING_STRATEGY.md) §4 for the
  comparison of training objectives, and in `INTELLIGENCE_DENSITY_RESEARCH.md` §6 as an example of
  **controlled ablation as a methodology** — the practice AETHER's experimental plan imitates at a
  thousandth of the scale.
- **Limitations / assumptions** — Pre-trains on C4 at up to 11 B parameters. Its conclusions about
  objective choice are measured at scale, and AETHER explicitly does not inherit them.

---

## 9. Parameter efficiency and representation

### [S46] Unified view of parameter-efficient transfer learning

- **Title** — Towards a Unified View of Parameter-Efficient Transfer Learning
- **Authors** — He, J.; Zhou, C.; Ma, X.; Berg-Kirkpatrick, T.; Neubig, G.
- **Year / venue** — 2021; ICLR 2022 (peer reviewed)
- **Identifier** — arXiv:2110.04366 · <https://arxiv.org/abs/2110.04366>
- **Contribution** — Re-frames adapter, prefix-tuning and LoRA-style methods as modifications to
  specific hidden states, identifies design dimensions along which they vary, and derives new methods
  that tune fewer parameters while matching full fine-tuning.
- **Relevance to AETHER** — `INTELLIGENCE_DENSITY_RESEARCH.md` §3 uses the framework to separate two
  things AETHER must not conflate: **parameter-efficient adaptation** (which AETHER may use later for
  task specialisation) and **parameter efficiency of the base model** (which is what actually matters
  under a storage budget). The paper is about the former and is not evidence about the latter.
- **Limitations / assumptions** — Assumes a large pre-trained model to adapt. Says nothing about
  training from random initialisation, which is AETHER's constraint.

### [S47] Building machines that learn and think like people

- **Title** — Building Machines That Learn and Think Like People
- **Authors** — Lake, B. M.; Ullman, T. D.; Tenenbaum, J. B.; Gershman, S. J.
- **Year / venue** — 2016; *Behavioral and Brain Sciences* (peer reviewed, with open commentary)
- **Identifier** — arXiv:1604.00289 · <https://arxiv.org/abs/1604.00289>
- **Contribution** — Argues that human-like learning requires causal world models, intuitive theories,
  and compositionality plus learning-to-learn, rather than end-to-end pattern recognition alone;
  proposes combining structured cognitive models with neural advances.
- **Relevance to AETHER** — The intellectual justification for AETHER's **component separation** —
  Core, Cognitive, Memory, Tools, Knowledge, Runtime — rather than one monolithic network
  ([`COGNITIVE_SYSTEM_SPEC.md`](COGNITIVE_SYSTEM_SPEC.md) §1). It is also the source of the strongest
  caution in Phase 2: a sophisticated surrounding architecture is **not** a more capable neural model,
  and `EVALUATION_PLAN.md` §7 forbids attributing ecosystem gains to the Core.
- **Limitations / assumptions** — A position paper, not an engineering result. Offers no evidence about
  what is achievable at 8 M parameters and no resource analysis of any kind.

---

## 10. Numerics and precision

### [S26] IEEE 754-2019

- **Title** — IEEE Standard for Floating-Point Arithmetic
- **Authors** — IEEE (standards body)
- **Year / venue** — 2019; IEEE standard (normative)
- **Identifier** — DOI 10.1109/IEEESTD.2019.8766229 · <https://doi.org/10.1109/IEEESTD.2019.8766229>
- **Contribution** — The normative definition of binary floating-point formats, rounding modes,
  arithmetic operations, and exceptional behaviour.
- **Relevance to AETHER** — Normative basis for every numeric claim in
  [`NUMERICAL_STRATEGY.md`](NUMERICAL_STRATEGY.md): `binary32` `u = 2⁻²⁴`, fp16's maximum finite value
  of 65504, and the rounding guarantees the equivalence tests rely on.
- **Limitations / assumptions** — Specifies what a conforming implementation *should* do. x87's
  extended-precision intermediate behaviour means a compiler may not conform exactly unless instructed
  (`-ffloat-store`, `-fexcess-precision=standard`); the standard does not resolve that toolchain
  question.

### Quantisation references — [S15]–[S19]

See [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §4 and §8 for full entries on LLM.int8() `[S15]`,
GPTQ `[S16]`, SmoothQuant `[S17]`, AWQ `[S18]` and BitNet b1.58 `[S19]`. Relevant limitation shared by
all five: every method assumes **GPU tensor cores and a 64-bit host**. None reports a 32-bit x86
implementation, and AETHER cites them for *method* only.

---

## 11. Tokenisation references — [S11]–[S14]

Full entries are in [`RESEARCH_SURVEY.md`](RESEARCH_SURVEY.md) §5 and §8. In brief: BPE `[S11]`,
unigram language model `[S12]`, SentencePiece `[S13]`, and the GPT-2 byte-level BPE report `[S14]`.
Shared limitation: none of these papers evaluates tokenisation under a **fixed vocabulary-memory
budget** or across Devanagari and Perso-Arabic scripts simultaneously, which is AETHER's actual
problem ([`TOKENIZER_SPEC.md`](TOKENIZER_SPEC.md) §2).

---

## 12. Sources deliberately not cited

The following were considered and excluded, and the reason is recorded so the exclusion is auditable:

| Source / claim | Why not cited |
| --- | --- |
| Secondary summaries claiming "Mamba is 5× faster" | Not stated by the primary paper in that form; `[S5]` is GPU-specific |
| Blog-post benchmark tables for small-model perplexity | Not peer reviewed, not reproducible, no stated conditions |
| LoRA (`2106.09685`) | Relevant to adapting a *pre-trained* model; AETHER trains from scratch `[S46]` covers the concept |
| Any "state of the art" headline figure | AETHER has produced no results and will not quote others' as its own context |

Two citation errors were caught during verification and are recorded here rather than silently
fixed: `1608.04016` is a paper on a Curry compiler (not SGDR, which is `1608.03983`), and `1804.02767`
is YOLOv3 (not an ELMo reference). Both were replaced with verified identifiers before use.

---

## 13. Unresolved questions

1. Which references should be promoted from preprint to peer-reviewed status as venues change? **[OPEN]**
2. Should this registry be machine-readable (e.g. a BibTeX file) once the document set stabilises? **Proposed: yes, Phase 3.** **[OPEN]**
3. `[S45]` and `[S21]` have no arXiv-issued DOI in the form used elsewhere; should DOIs be added from
   the publisher of record? **[OPEN]**
4. Is `[S14]` (the GPT-2 technical report) an acceptable citation target given it has no arXiv ID and
   no peer review? It is used only for the byte-level BPE fact. **Proposed: acceptable, with the
   caveat stated wherever it is used.** **[OPEN]**
