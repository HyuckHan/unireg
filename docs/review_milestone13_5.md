# Milestone 13.5 Review: Explainability and Error Analysis

## What Was Implemented

Milestone 13.5 added a deterministic QA explainability and error-analysis
framework.

Implemented components:

- `unireg.analysis` package.
- Normalized QA trace dataclasses.
- Error taxonomy with required categories.
- Multi-label automatic error classifier.
- Trace JSONL loader with malformed-line handling.
- Optional benchmark enrichment for older traces that lack gold citations or
  answerability labels.
- JSON, CSV, and Markdown report writers.
- CLI entry points:
  - `scripts/unireg_analyze_errors.py`
  - `python -m unireg.analysis`
  - `unireg-error-analysis`
  - `unireg analyze-errors`
- pytest coverage for taxonomy, single-label classification, multi-label
  classification, missing regulation cases, hallucination cases, citation
  mismatch, report generation, empty trace handling, malformed trace handling,
  and CLI output.
- QA evaluation row extension with `answerability` and `gold_citations` so new
  QA traces are self-contained for later analysis.

## Architectural Decisions

The analyzer is isolated under `unireg.analysis`.

This keeps explanation logic separate from parser, retrieval, and QA execution.
Milestone 13.5 consumes traces; it does not change how answers are generated.

The parser remains canonical.

Parser output is not modified. Parser-related failures are inferred from missing
source-page or citation metadata in the evidence trace.

Retrieval remains independent.

The analyzer reads retrieved evidence and rank metadata but does not modify the
BM25 implementation or retrieval runner.

Classification is deterministic and rule-based.

The goal is publication-quality diagnosis, not answer improvement. A rule-based
classifier makes every category assignment auditable and reproducible.

The classifier is multi-label.

Many QA failures have multiple causes. For example, a missing-regulation
question can also suffer from a retrieval miss or hallucinated completeness
status. The report preserves those overlaps instead of forcing a single cause.

Reports are generated from a single report object.

JSON is suitable for downstream processing, CSV is suitable for spreadsheet
inspection, and Markdown is suitable for paper notes and experiment summaries.

## Trade-Offs

The classifier favors explainability over model-like flexibility.

Rule-based classification is easier to audit and reproduce than a learned
classifier, but it cannot capture every semantic failure mode in a natural
language answer.

The analyzer uses existing trace data instead of re-running parser or retrieval.

This keeps analysis cheap and deterministic. The trade-off is that parser and
retrieval root-cause labels are inferred from trace evidence, so they should be
treated as likely causes rather than definitive human audit findings.

`MISSING_REGULATION` is not treated as an error by itself.

Missing downstream regulations are expected in incomplete corpora. The analyzer
therefore labels `MISSING_REGULATION` only when it helps explain a failed trace,
such as a complete answer for a missing-regulation question.

Benchmark labels take priority over textual incompleteness signals.

This avoids over-classifying answerable questions as missing-regulation failures
when lower-ranked evidence happens to mention delegated details. The trade-off
is that mislabeled benchmark questions can suppress useful incompleteness
signals until the gold labels are corrected.

## Error Taxonomy

Supported categories:

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

`NO_ERROR` is exclusive. All other categories may be combined.

## Known Limitations

- The classifier identifies likely causes from traces, not from human semantic
  review.
- Hallucination detection is conservative and status/citation based. It does not
  judge every natural-language claim inside an answer.
- `MISSING_REGULATION` is treated as an error context only when it contributes
  to a failed trace.
- Parser errors are inferred from missing source spans and metadata, not from
  re-parsing source PDFs.
- Retrieval ranking error is reported when gold evidence is retrieved below
  rank 1 and the QA citation remains wrong.
- Answer text correctness is still not evaluated against gold natural-language
  answers.
- The current benchmark has only 20 QA questions, so distribution tables are
  diagnostic rather than statistically strong.

## Future Work

- Add optional human-review annotations to confirm or override automatic error
  classifications.
- Add gold answer text and answer-span annotations so semantic answer
  correctness can be evaluated separately from citation and completeness
  correctness.
- Add per-retrieval-unit error comparisons for article-only, clause-only,
  mixed-unit, and future hybrid retrieval runs.
- Add schema files for QA traces and error-analysis reports.
- Add stable experiment manifests that bind a QA trace file, retrieval config,
  benchmark version, and error-analysis report.
- Add confusion matrices for completeness labels once the benchmark has more
  missing-regulation and partially-answerable questions.
- Add paper-ready export tables with fixed ordering and rounded metrics for
  reproducible experiment appendices.

## Examples Of Generated Reports

Run:

```bash
.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

Outputs:

- `benchmark/reports/error_analysis/error_analysis.json`
- `benchmark/reports/error_analysis/error_analysis.csv`
- `benchmark/reports/error_analysis/error_analysis.md`

Current local MockLLM trace result after the Milestone 13.5 analyzer:

```text
traces=20
success=12
failure=8
malformed=0
```

Markdown tables include:

- `Error Category | Count | Percentage`
- `Answerability Type | Accuracy | Major Error Type`
- `Retriever | Recall@3 | QA Accuracy | Main Failure Mode`
- `University | Accuracy | Main Failure Mode`

## Recommendations For Milestone 14 Experiments

Use Milestone 13.5 reports as the diagnostic layer for every experiment.

Recommended next steps:

- Run error analysis for every retrieval configuration:
  - article only
  - clause only
  - article plus clause
  - article plus clause plus item plus sub-item
- Compare `question_source` and `corpus` retrieval scopes.
- Add more questions before interpreting category distributions as paper-level
  evidence.
- Add manually reviewed gold answer text if semantic answer correctness will be
  reported.
- Use the Markdown report to select representative qualitative examples for the
  paper.
- Keep online LLM provider comparisons out of Milestone 14 until the experiment
  protocol fixes trace format, report format, and benchmark splits.
