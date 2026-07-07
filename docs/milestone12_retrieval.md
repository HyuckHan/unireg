# Milestone 12: Retrieval Evaluation

Status: Implemented

## Goal

Evaluate retrieval quality independently from LLMs.

LLMs are not involved in this milestone. The retrieval baseline is deterministic
and uses only parsed regulation structures plus benchmark questions from
Milestone 11.

## Implemented Scope

- BM25 retrieval baseline.
- Retrieval evaluation runner.
- Benchmark question support from UniRegBench.
- Retrieval units:
  - article
  - clause
  - item
  - sub-item
- Metrics:
  - Recall@1
  - Recall@3
  - Recall@5
  - MRR
  - nDCG@5
- JSONL prediction output.
- JSON report output.
- CSV per-question report.
- CSV per-hit report.
- pytest coverage for BM25, retrieval units, benchmark evaluation, and report
  generation.

Out of scope:

- LLM QA.
- Dense retrieval.
- Hybrid retrieval.
- External APIs.
- Parser changes.

## Architecture

Retrieval code is isolated under `unireg.retrieval`.

Modules:

- `unireg.retrieval.bm25`
  - tokenization
  - in-process BM25 index
  - ranked BM25 search hits
- `unireg.retrieval.corpus`
  - projection-to-retrieval-unit conversion
  - benchmark source parsing
  - retrieval unit selection
- `unireg.retrieval.runner`
  - benchmark question execution
  - prediction generation
  - metric evaluation
  - JSON/CSV report writing
- `unireg.retrieval.cli`
  - command-line interface

The parser is unchanged. Retrieval units are built from existing
`ProjectionBuilder` BM25 documents.

## Retrieval Units

The runner supports the following unit types:

```text
article,clause,item,sub_item
```

The default uses all four. CLI users can restrict the unit set:

```bash
--units article
--units clause
--units article,clause
--units article,clause,item,sub_item
```

## BM25 Baseline

BM25 is implemented without external dependencies.

The tokenizer emits:

- Korean/Latin/digit word tokens
- Korean character bigrams
- Korean character trigrams

The n-grams make retrieval more robust for Korean legal text where PDF
extraction and spacing may be inconsistent.

## Evaluation Semantics

Gold citation matching is hierarchical.

- If gold specifies only an article, any retrieved unit under that article can
  match.
- If gold specifies a clause, the retrieved unit must be that clause or a
  descendant under that clause.
- If gold specifies `source_file`, the retrieved unit must come from that source
  file.
- If gold specifies `node_id`, matching is exact.

This keeps article-level and fine-grained retrieval comparable while preventing
the same article number from another university from being counted as correct.

## CLI

Run the BM25 baseline:

```bash
.venv/bin/python scripts/unireg_retrieval.py bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl \
  --units article,clause,item,sub_item \
  --scope question_source \
  --top-k 5
```

The same runner can be used as a module:

```bash
.venv/bin/python -m unireg.retrieval bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl
```

When installed as a package:

```bash
unireg-retrieval bm25 --benchmark-dir benchmark
```

## Retrieval Scope

Supported scopes:

- `question_source`
  - Search only the source file attached to each benchmark question.
  - This is the default for the current university-specific benchmark.
- `corpus`
  - Search all benchmark source files.
  - Useful for measuring cross-university disambiguation.

## Outputs

The runner writes:

- `benchmark/retrieval/predictions.bm25.jsonl`
- `benchmark/reports/retrieval_bm25_report.json`
- `benchmark/reports/retrieval_bm25_questions.csv`
- `benchmark/reports/retrieval_bm25_hits.csv`

Generated BM25 predictions and reports are ignored by git.

## Current Baseline Result

Command:

```bash
.venv/bin/python scripts/unireg_retrieval.py bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl \
  --units article,clause,item,sub_item \
  --scope question_source \
  --top-k 5
```

Observed local result on the five-university `학칙.pdf` benchmark:

```text
questions=20
documents=2316
Recall@1=0.700
Recall@3=1.000
Recall@5=1.000
MRR=0.842
nDCG@5=0.883
```

These numbers are a deterministic retrieval baseline, not an LLM QA result.

## Future Retrieval Methods

Future milestones may add:

- dense retrieval
- hybrid retrieval
- graph retrieval
- hierarchical retrieval
- metadata-aware reranking

Those methods should emit the same `RetrievalPrediction` JSONL format so they
can be compared against the BM25 baseline.
