# Milestone 11 Review: UniRegBench

## What Was Implemented

Milestone 11 introduced UniRegBench as the project benchmark layer.

Implemented components:

- `benchmark/` directory layout for parser, question, retrieval, QA, and report
  artifacts.
- JSONL benchmark fixtures for parser cases and benchmark questions.
- JSON schema files for question, parser-case, and retrieval-prediction records.
- `unireg.benchmark` package with dataclasses, loaders, validation, evaluation,
  and report writers.
- CLI entry points:
  - `scripts/unireg_benchmark.py`
  - `python -m unireg.benchmark`
  - `unireg-benchmark` package script
- Parser benchmark evaluation over local university `학칙.pdf` files.
- Retrieval metric evaluation for supplied ranked citation predictions.
- JSON, CSV, and Markdown benchmark reports.
- Multi-university benchmark fixtures for five local `unireg-eval`
  universities:
  - Dongduk Women's University
  - Dongyang Mirae University
  - Duksung Women's University
  - Kwangwoon University
  - Seoul Women's University

The benchmark currently includes 5 parser cases and 20 university-specific
questions. Gold citations include `source_file` to distinguish identical article
numbers across universities.

## Architectural Decisions

UniRegBench is isolated under `unireg.benchmark`.

This keeps evaluation code separate from the parser, exporters, citations, and
future retrieval code. Parser quality can now be measured without coupling the
parser to benchmark-specific assumptions.

Benchmark records are represented as dataclasses.

This matches the project convention and provides a stable boundary between JSONL
fixtures and Python evaluation code. The current dataclasses are intentionally
small:

- `BenchmarkQuestion`
- `GoldCitation`
- `RetrievalPrediction`
- `ParserBenchmarkCase`

Benchmark data is stored as JSONL.

JSONL keeps fixtures reviewable, append-only, and friendly to later generated
experiment outputs. It is also easy to split by institution, task, or corpus
without changing the loader because the loader reads all `*.jsonl` files in the
benchmark subdirectories.

Parser evaluation uses structural thresholds plus required citations.

Exact chapter counts are not yet stable enough across PDFs because some source
documents attach chapter headings inline with article text. For Milestone 11,
the benchmark therefore checks minimum article/clause/citation counts and
required legal citations instead of enforcing exact chapter counts for every
university.

Retrieval evaluation uses exact gold citation matching.

This is appropriate for the first reproducible benchmark because it keeps
metrics deterministic. `source_file` is part of the citation key so a prediction
for the same article number in a different university is not counted as correct.

Generated reports are ignored by git.

The benchmark source data and schemas are versioned. Machine-local reports under
`benchmark/reports/` are regenerated outputs and should not create repository
noise.

## Trade-Offs

The benchmark favors reproducibility over full experiment realism.

The sample retrieval prediction file is a gold-first fixture. It verifies that
the CLI, loader, metrics, and report writers work, but it is not a real retrieval
baseline. Actual search and RAG experiments must replace this file with real
ranked outputs.

The benchmark uses local PDFs under `unireg-eval`.

This is practical for testing real university documents without committing PDF
files to the repository. The trade-off is that a fresh checkout cannot reproduce
the full benchmark unless the same `unireg-eval` corpus is available locally.

The parser benchmark avoids exact chapter-count assertions.

This prevents known PDF extraction quirks from making the whole benchmark
unusable. The downside is that chapter-level errors can pass if article, clause,
and required-citation checks still succeed.

The current validation is lightweight.

Validation catches duplicate IDs, missing parser source files, empty questions,
and invalid citation anchors. It does not yet enforce the JSON schema through a
schema engine or verify that every gold citation exists in the parsed corpus.

## Known Limitations

- `unireg-eval` PDFs are ignored by git, so the full benchmark depends on local
  corpus availability.
- Retrieval evaluation currently measures supplied predictions only; there is no
  built-in search index or retriever.
- `predictions.sample.jsonl` is not a baseline model result.
- QA evaluation is not implemented yet.
- Answer text quality, citation faithfulness, and answerability classification
  are not scored yet.
- Parser benchmark cases use threshold checks rather than manually audited exact
  counts for every structural level.
- Inline chapter headings can still collapse chapter structure, as seen in the
  Kwangwoon fixture.
- Gold question coverage is intentionally small: four core question types per
  university.
- The benchmark has no train/dev/test split yet.
- The benchmark does not yet store annotator notes, evidence snippets, or manual
  review status beyond simple metadata.

## Future Work

- Add a corpus manifest for `unireg-eval` that records expected university IDs,
  regulation names, source filenames, and optional checksums.
- Add a stricter benchmark validation pass that verifies gold citations against
  parser output.
- Add real retrieval baselines:
  - BM25
  - vector retrieval
  - hybrid retrieval
  - metadata-filtered retrieval
- Add held-out universities for cross-university generalization experiments.
- Expand question sets beyond the current core topics:
  - leave of absence
  - graduation credits
  - degree conferral
  - missing regulation references
  - multi-hop questions
  - comparison questions
- Add QA evaluation artifacts and metrics:
  - answerability label accuracy
  - citation correctness
  - grounded answer completeness
  - missing-regulation detection
- Improve parser robustness for inline headings before treating chapter counts
  as hard benchmark assertions.
- Add annotation guidelines for human-created gold questions and citations.

## Recommendations For The Next Milestone

The next milestone should focus on retrieval, not QA generation yet.

Recommended scope:

- Build a real retrieval pipeline over parsed regulations.
- Generate ranked citation predictions in the existing
  `benchmark/retrieval/*.jsonl` format.
- Implement at least one deterministic baseline, preferably BM25 first.
- Preserve institution, source file, article number, hierarchy path, and citation
  label in retriever metadata.
- Add CLI support to produce prediction files separately from benchmark
  evaluation.
- Compare real retrieval output against the current UniRegBench questions.

Do not start grounded QA until retrieval has a measurable baseline. The QA
system will depend on citation ranking quality, and weak retrieval would make QA
evaluation noisy and hard to interpret.
