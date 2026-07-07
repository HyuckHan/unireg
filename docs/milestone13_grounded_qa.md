# Milestone 13: Grounded QA Framework

Status: Implemented

## Goal

Build a grounded QA layer on top of retrieval without depending on online LLM
inference.

The QA pipeline is LLM-independent. Any future provider adapter must consume the
same Evidence Package and return the same structured Grounded Answer schema.

## Pipeline

```text
Question
  -> Retriever
  -> Evidence Package
  -> LLM Adapter
  -> Grounded Answer
  -> Evaluation
```

The parser remains canonical. Retrieval remains independent. QA consumes
retrieved evidence and does not modify parser or retrieval architecture.

## Implemented Modules

- `unireg.qa.models`
  - Evidence Package schema
  - LLM request/response schema
  - Grounded Answer schema
  - completeness labels
- `unireg.qa.evidence`
  - retrieval-hit to evidence-package conversion
- `unireg.qa.adapters`
  - abstract LLM adapter interface
  - deterministic MockLLM adapter
  - future provider boundary
- `unireg.qa.retrievers`
  - QA retriever abstraction
  - BM25 retriever adapter
- `unireg.qa.pipeline`
  - Question -> evidence -> LLM request -> answer
  - guardrail enforcement
- `unireg.qa.evaluation`
  - citation accuracy
  - groundedness
  - completeness classification
  - hallucination rate
- `unireg.qa.cli`
  - single-question QA
  - benchmark QA
- `unireg.cli`
  - top-level `unireg qa` entry point

## Evidence Package

The Evidence Package is the only content the LLM adapter is allowed to consume.

Each package contains:

- package id
- question
- retriever name
- retrieval scope
- top-k value
- retrieved evidence items
- metadata

Each evidence item contains:

- evidence id
- rank
- retrieval score
- normalized confidence
- node id
- node type
- text
- citation
- citation label
- source file
- source pages
- source label
- parser/retrieval metadata
- incompleteness flags

## Traceability

Every `GroundedAnswer` serializes a full trace:

```text
Question
  -> Retrieved Evidence
  -> Evidence Package
  -> exact LLM Input
  -> raw LLM Output
  -> guarded Grounded Answer
  -> Evaluation
```

The benchmark QA answers JSONL contains one complete trace per line. A
researcher can reconstruct the question, retrieval results, prompt payload,
answer, citations, and evaluation row without relying on external state.

## LLM Adapter Interface

The adapter boundary supports these providers at the interface level:

- mock
- OpenAI future
- Anthropic future
- Gemini future
- local LLM future

Only `MockLLMAdapter` is implemented in this milestone.

The MockLLM adapter:

- calls no external APIs
- uses only the Evidence Package
- returns deterministic structured output
- emits incomplete answers when evidence is missing or indicates unresolved
  regulation dependencies

## Grounded Answer Schema

Each answer contains:

- answer id
- question
- answer text
- citations
- evidence list
- completeness status
- confidence
- reasoning metadata
- evidence package
- exact LLM request
- raw LLM response
- guardrail events
- optional evaluation row

Completeness statuses:

- `complete`
- `partial`
- `missing_regulation`
- `unknown`

## Hallucination Protection

The framework never accepts unsupported citations from an adapter.

Guardrails:

- remove citations that do not appear in the Evidence Package
- force `unknown` when no evidence exists
- downgrade `complete` answers without supported citations to `partial`
- preserve guardrail events in the answer trace

If evidence is insufficient, the framework returns an explicit incomplete
answer instead of fabricating a regulation.

## QA Evaluation

Implemented metrics:

- citation accuracy
- groundedness
- completeness classification accuracy
- hallucination rate

Evaluation output:

- aggregate JSON report
- per-question CSV
- answer trace JSONL with evaluation rows embedded

## CLI

Single-question QA:

```bash
.venv/bin/python scripts/unireg_qa.py \
  --question questions/example.txt \
  --retriever bm25 \
  --llm mock \
  --benchmark-dir benchmark \
  --output /tmp/unireg-qa-answer.json
```

Benchmark QA:

```bash
.venv/bin/python scripts/unireg_qa.py \
  --benchmark \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --retriever bm25 \
  --llm mock \
  --scope question_source \
  --top-k 5
```

Installed console scripts:

```bash
unireg qa --question questions/example.txt --retriever bm25
unireg-qa --benchmark --benchmark-dir benchmark
```

## Current Mock QA Result

Observed local result on the five-university `학칙.pdf` benchmark:

```text
questions=20
citation_accuracy=0.700
groundedness=1.000
completeness_classification=0.800
hallucination_rate=0.000
```

These numbers evaluate the framework plus MockLLM behavior. They are not an
online LLM result.

## Future Work

- Add real provider adapters without changing the pipeline contract.
- Add extractive answer templates for stronger MockLLM baselines.
- Add answer text evaluation when a gold answer set exists.
- Add hybrid/dense retrieval input to the same QA pipeline.
- Add manual annotation guidelines for QA completeness labels.
