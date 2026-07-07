# Milestone 13 Review: Grounded QA Framework

## What Was Implemented

Milestone 13 added an LLM-independent grounded QA framework on top of the
retrieval layer.

Implemented components:

- `unireg.qa` package.
- Evidence Package schema.
- Evidence item schema with retrieved node text, citation, source pages,
  metadata, incompleteness flags, score, and confidence.
- Abstract LLM adapter interface.
- Deterministic `MockLLMAdapter`.
- Future provider boundary for OpenAI, Anthropic, Gemini, and local LLMs.
- Grounded Answer schema.
- QA pipeline:
  - question
  - retriever
  - evidence package
  - LLM adapter
  - grounded answer
- Hallucination guardrails.
- QA evaluation metrics:
  - citation accuracy
  - groundedness
  - completeness classification
  - hallucination rate
- Single-question QA CLI.
- Benchmark QA CLI.
- Traceable JSON, CSV, and JSONL reports.
- Tests for evidence package creation, MockLLM behavior, guardrails, evaluation,
  and benchmark QA reporting.

Current local MockLLM benchmark result:

```text
questions=20
citation_accuracy=0.700
groundedness=1.000
completeness_classification=0.800
hallucination_rate=0.000
```

## Architectural Decisions

QA is isolated under `unireg.qa`.

The parser remains canonical. Retrieval remains independent. QA consumes the
retriever output and does not change parser or retrieval architecture.

The Evidence Package is the only LLM input.

The adapter receives a structured package containing retrieved evidence, source
metadata, citations, source pages, confidence, and incompleteness flags. This
keeps the LLM boundary auditable and provider-independent.

The LLM adapter is abstract.

`LLMAdapter` defines the stable provider contract. `MockLLMAdapter` is the only
implemented adapter in this milestone. Future OpenAI, Anthropic, Gemini, and
local adapters should implement the same request/response schema without
changing the pipeline.

Every answer is traceable.

`GroundedAnswer.to_dict()` includes:

- original question
- retrieved evidence
- Evidence Package
- exact LLM request
- raw LLM response
- guarded answer
- guardrail events
- optional evaluation row

Benchmark answer JSONL embeds evaluation in each answer trace, so researchers
can reconstruct the full path from question to evaluation.

Guardrails live after the adapter.

This makes hallucination protection provider-independent. If any future adapter
returns citations outside the Evidence Package, the framework removes them and
records the event.

## Trade-Offs

The MockLLM is intentionally conservative.

It gives deterministic, traceable answers but does not attempt high-quality
natural-language synthesis. This is appropriate for framework validation, but it
is not a substitute for provider or local model evaluation.

Citation accuracy is bounded by retrieval quality.

The current MockLLM uses top evidence. Its citation accuracy therefore closely
tracks BM25 top-rank quality. This is useful as a baseline but means retrieval
errors become QA citation errors.

Completeness classification depends on evidence signals.

The framework uses parser incompleteness metadata and textual signals such as
`따로 정한다`. This avoids fabricating answers, but it can be conservative when
retrieved evidence mentions delegation in a broader context.

Evaluation is citation/status focused.

There is no gold free-form answer text yet, so the framework does not score
semantic answer correctness beyond citation accuracy, groundedness, completeness
classification, and hallucination rate.

## Known Limitations

- Online LLM adapters are not implemented.
- Local LLM inference is not implemented.
- The MockLLM is extractive and template-based.
- Answer text quality is not evaluated.
- QA benchmark coverage is still small.
- Retrieval misses directly reduce QA citation accuracy.
- Completeness labels may need manual audit as the benchmark expands.
- The framework does not yet support multi-hop answer composition.
- Corpus-wide QA needs more disambiguation testing.

## Future Work

- Add provider adapters only after finalizing API key and reproducibility policy.
- Add a local LLM adapter if a deterministic local inference setup is selected.
- Add gold answer annotations for semantic answer quality evaluation.
- Expand UniRegBench QA questions:
  - paraphrase questions
  - multi-hop questions
  - comparison questions
  - missing-regulation cases
- Improve retrieval reranking before relying on QA-level synthesis.
- Add evidence compression for long retrieved nodes.
- Add citation rendering for UI and paper examples.
- Add schema files for QA answers and evidence packages.

## Recommendations For The Next Milestone

The next milestone should focus on experimental rigor before adding online
inference.

Recommended next steps:

- Expand benchmark QA annotations.
- Compare QA over different retrieval configurations.
- Add per-unit ablations:
  - article only
  - clause only
  - article plus clause
  - article plus clause plus item plus sub-item
- Add corpus-scope QA runs for cross-university disambiguation.
- Decide whether to implement a local LLM adapter or keep provider adapters out
  until the paper experiment protocol is stable.

Do not introduce online LLM calls until the Evidence Package, trace format, and
evaluation metrics are stable enough to make provider comparisons meaningful.
