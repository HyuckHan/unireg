# Milestone 13.5: Explainability and Error Analysis

Status: Implemented

## Goal

Explain why each UniReg grounded QA result succeeded or failed.

This milestone does not improve answers directly. It consumes Milestone 13 QA
traces and produces deterministic, publication-oriented error analysis.

## Inputs

The analyzer reads Milestone 13 answer trace JSONL, for example:

```bash
benchmark/reports/qa_mock_answers.jsonl
```

Each trace is normalized into:

- question id
- question text
- answerability label
- retrieved evidence
- gold citations
- predicted citations
- completeness status
- grounded answer
- evidence package
- retriever metadata
- LLM adapter metadata
- evaluation results

Older Milestone 13 traces may not contain `answerability` or `gold_citations`
inside each answer row. The analyzer can enrich those fields from
`--benchmark-dir benchmark`. New QA evaluation rows include both fields so new
traces are self-contained.

## Error Taxonomy

Supported error categories:

- `NO_ERROR`
- `PARSER_ERROR`
- `METADATA_ERROR`
- `RETRIEVAL_MISS`
- `RETRIEVAL_RANKING_ERROR`
- `CITATION_MISMATCH`
- `INSUFFICIENT_EVIDENCE`
- `MISSING_REGULATION`
- `COMPLETENESS_MISCLASSIFICATION`
- `HALLUCINATION`
- `UNSUPPORTED_ANSWER`
- `AMBIGUOUS_GOLD`
- `UNKNOWN_ERROR`

The classifier is multi-label. A single failed answer can receive multiple
categories, such as:

- `RETRIEVAL_MISS` + `MISSING_REGULATION`
- `CITATION_MISMATCH` + `UNSUPPORTED_ANSWER`
- `COMPLETENESS_MISCLASSIFICATION` + `HALLUCINATION`

`NO_ERROR` is assigned only when no failure category is present.

## Classification Rules

The classifier uses deterministic trace evidence:

- Gold citation absent from retrieved evidence:
  - `RETRIEVAL_MISS`
- Gold citation retrieved below rank 1 and QA citation is wrong:
  - `RETRIEVAL_RANKING_ERROR`
- Gold citation appears in evidence but predicted citation differs:
  - `CITATION_MISMATCH`
- Predicted citation is not supported by retrieved evidence:
  - `UNSUPPORTED_ANSWER`
- Expected and predicted completeness labels differ:
  - `COMPLETENESS_MISCLASSIFICATION`
- Missing-regulation question is answered as complete:
  - `HALLUCINATION`
  - `COMPLETENESS_MISCLASSIFICATION`
  - `MISSING_REGULATION`
- Evidence package is empty:
  - `INSUFFICIENT_EVIDENCE`
- Cited evidence lacks source-page metadata:
  - `PARSER_ERROR`
- Citation or trace metadata lacks required anchors:
  - `METADATA_ERROR`
- Gold citation is empty or underspecified for an answerable question:
  - `AMBIGUOUS_GOLD`

## Architecture

Code is isolated under `unireg.analysis`.

Modules:

- `unireg.analysis.models`
  - error taxonomy
  - normalized trace dataclasses
  - classification and report dataclasses
- `unireg.analysis.loader`
  - QA trace JSONL ingestion
  - benchmark-based gold/answerability enrichment
  - malformed trace handling
- `unireg.analysis.classifier`
  - deterministic multi-label classification rules
- `unireg.analysis.runner`
  - aggregate analysis orchestration
  - success/failure counts
  - answerability/retriever/university breakdowns
- `unireg.analysis.reports`
  - JSON report
  - CSV report
  - Markdown report
- `unireg.analysis.cli`
  - command-line interface

The parser and retrieval architectures are unchanged.

## CLI

Standalone script:

```bash
.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

Module:

```bash
.venv/bin/python -m unireg.analysis \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis
```

Top-level CLI:

```bash
unireg analyze-errors \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis
```

Installed console script:

```bash
unireg-error-analysis \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis
```

## Outputs

The analyzer writes:

- `error_analysis.json`
- `error_analysis.csv`
- `error_analysis.md`

The Markdown report includes tables for:

- error category distribution
- answerability type accuracy and major error type
- retriever Recall@3, QA accuracy, and main failure mode
- per-university accuracy and main failure mode
- top failed questions
- representative examples for each error category

## Reproducibility

The analysis is deterministic:

- no external APIs
- no online LLM inference
- no random sampling
- no parser or retrieval mutation

Generated reports under `benchmark/reports/` remain ignored by git.

## Current Usage

Recommended sequence:

```bash
.venv/bin/python scripts/unireg_qa.py \
  --benchmark \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --retriever bm25 \
  --llm mock \
  --scope question_source \
  --top-k 5

.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

This reconstructs:

```text
Question
  -> Retrieved Evidence
  -> Predicted Answer
  -> Evaluation Result
  -> Error Classification
```

without ambiguity.
