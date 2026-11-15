# AETHER — Research Principles

AETHER is a research project, so its standard of evidence is the core of its credibility. These
principles apply to experiments, benchmarks, design arguments, and documentation.

They exist because it is easy — and common — to publish AI results that look impressive and cannot
be reproduced. The project would rather publish a modest, checkable result than an impressive,
unverifiable one.

---

## 1. Reproducibility

A result is only a result if someone else can obtain it.

- **Record everything that affects the outcome:** code commit, data version and hash, seeds,
  hyperparameters, toolchain and version, build flags, hardware, and operating system.
- **Provide the exact command** that produces the reported number.
- **Seeds and determinism.** Where execution is nondeterministic, say so, report the variation, and
  explain the source (threading, floating-point reduction order, hardware differences).
- **Data is versioned** by immutable identifier, per [`DATA_POLICY.md`](DATA_POLICY.md).
- **Environment is described.** "It ran on a machine" is not a configuration description. CPU
  model, core count, and memory matter, especially for CPU-first work.
- **Reproduction status is stated honestly**, in one of three forms: *reproduced independently*,
  *reproduced by the author only*, or *not reproduced*. All three are acceptable to publish; only
  the first may be called verified.
- **Artifacts stay available.** If an experiment depends on files, they are either committed (small,
  license-permitting) or their provenance and hash recorded.

**Anti-pattern:** a number that appears in a README with no path back to a command, a commit, and a
dataset version.

## 2. Baseline comparisons

Every claim of improvement is a claim *relative to something*. Name that something.

- **Report a baseline.** At minimum a trivial or random baseline; where relevant, a documented
  reference implementation.
- **Baselines run under the same conditions** as the proposal: same hardware, same data splits, same
  evaluation harness, same precision, same prompting.
- **Do not compare against numbers copied from another paper** unless the comparison is explicitly
  labelled as cross-paper and the differences in setup are stated. Different harnesses produce
  different numbers for the same model.
- **A baseline that is deliberately weakened is not a baseline.** If it must be weakened (for cost,
  for example), say so and state the effect.
- **If no reasonable baseline exists**, say that, and explain why the result is still informative.

## 3. Measurable claims

- **Every quantitative claim names its metric, dataset, and conditions.** "Faster" is not a
  measurement; "2.1 s median latency per 128-token generation on [CPU model], warm cache, single
  thread" is.
- **Report the spread, not just the center.** Multiple runs, with median and range, or mean and
  standard deviation. A single run is an anecdote.
- **Keep units and precision honest.** Do not report more digits than the measurement supports.
- **State what was measured, not what was hoped for.** Intended performance is not measured
  performance.
- **Avoid composite or custom metrics** unless their definition is given and justified.
- **Round toward caution.** If a measurement is between two values, report the less flattering one
  when describing a benefit, and explain the uncertainty.

## 4. Honest reporting

- **Report negative and null results.** A failed idea is a usable finding, and prevents repetition.
- **Report the conditions where the result did not hold.** A gain on one task with a loss on another
  is a two-part result, not a one-part result.
- **Do not cherry-pick seeds, prompts, or checkpoints.** If the best of ten runs is reported, say so
  and report the others.
- **Disclose dead ends and abandoned designs**, briefly, where they cost real effort.
- **Distinguish observed from inferred.** "The model produced X" is an observation; "the model
  learned Y" is an inference.
- **Correct errors publicly.** If a published result is wrong, update the document with a correction
  note rather than quietly editing the number.
- **No retroactive softening.** Do not remove an inconvenient limitation from a document when a new
  result supersedes it; supersede it explicitly.

## 5. Ablations and controls

- **Change one thing at a time.** A result produced by several simultaneous changes cannot be
  attributed.
- **Ablate what you claim matters.** If the design argument says a component is responsible for a
  benefit, show the benefit without it.
- **Include controls for the harness itself.** A no-op change should produce a no-op result; if it
  does not, the measurement is broken.
- **Cost-aware ablations.** Not every combination can be run on CPU-only hardware; prioritize the
  ones that test the central claim, and say which were not run.

## 6. Evaluation across multiple task categories

A single benchmark measures a single kind of thing.

- **Evaluate on more than one task category** before making a general capability statement. Token
  prediction quality is not instruction following; a perplexity number is not a task result.
- **Report per-task results**, not only an average. An average can hide a category that regressed.
- **Include at least one task where a naive or trivial approach scores well**, to test whether the
  evaluation actually discriminates.
- **Guard against contamination** between training and evaluation data.
- **State evaluation limits:** sample size, prompt sensitivity, number of shots, decoding settings,
  and whether the harness was validated.

## 7. No misleading benchmark comparisons

This is where most AI claims go wrong. Concretely, this project will not:

- Compare **different model sizes** and present it as an algorithmic improvement.
- Compare runs on **different hardware** and present it as efficiency.
- Compare against **numbers from other papers** without labelling them as such and stating setup
  differences.
- Report **throughput without latency**, or latency without stating the input length, batch size,
  thread count, and cache state.
- Report **memory** without stating whether it is peak resident, weights only, or estimated.
- Present **quantized results next to unquantized baselines** without labelling which is which.
- Claim **32-bit compatibility** from a 64-bit build, or from a build that was never executed.
- Use **"up to"** figures as if they were typical.
- Present **a single favourable configuration** as representative.
- Imply **parity or superiority** with any named system without a like-for-like measurement in this
  repository.

If a comparison cannot be made honestly, it is not made at all. "Not comparable" is a valid and
acceptable finding.

## 8. Documentation of experiments

Each experiment record includes:

1. **Question** — what it was testing.
2. **Hypothesis** — expected outcome and what would falsify it.
3. **Configuration** — code, data, hyperparameters, environment.
4. **Command** — the exact invocation.
5. **Results** — raw numbers, with spread.
6. **Interpretation** — what it does and does not support.
7. **Limitations** — what was not tested.

Records live in the repository, not in a private notebook. Where an experiment is exploratory and
not worth a full document, a short note in the pull request description is acceptable, provided it
is findable from the relevant code.

## 9. Review

- Research claims are reviewed like code. A reviewer should be able to ask "where is the command
  for this number?" and get an answer.
- Reviewers are expected to challenge comparisons, seed counts, and baseline strength.
- A claim that cannot be substantiated is removed or marked unverified. It is not softened into
  something vaguer and left in place.

## 10. Summary

> Measure it. Record how. Compare it to something honest. Report what happened, including when it
> did not work.

Everything in this document follows from those four sentences.
