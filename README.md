# UniReg

UniReg is an open-source parser and knowledge platform for university regulations.

Its primary goal is to transform university regulations (PDF/HWP) into structured knowledge that can be searched, linked, and queried by Large Language Models.

## Features

- Parse university regulations from PDF/HWP
- Extract hierarchy
    - Chapter
    - Section (optional)
    - Article
    - Clause
    - Item
- Preserve amendment history
- Export Markdown
- Export JSON
- Build knowledge graph
- Support RAG
- Citation-aware answers

## Project Stages

1. Regulation Parser
2. Structured Data Model
3. Search Engine
4. RAG
5. Web UI
6. Obsidian Export

## Philosophy

LLM should never invent regulations.

Every answer must be grounded by the original regulation.

## PDF Corpus Smoke Test

Copy regulation PDFs into `examples/pdf`, then run:

```bash
.venv/bin/python scripts/check_pdfs.py --pdf-dir examples/pdf
```

To save a CSV report:

```bash
.venv/bin/python scripts/check_pdfs.py \
  --pdf-dir examples/pdf \
  --report /tmp/unireg-pdf-report.csv \
  --quiet
```

The full corpus pytest is opt-in so normal tests stay fast:

```bash
UNIREG_RUN_PDF_CORPUS=1 .venv/bin/python -m pytest tests/test_pdf_corpus.py
```

## External University Evaluation

Put external university samples under one folder per university:

```text
unireg-eval/
  university_a/
    학칙.pdf
  university_b/
    학칙.pdf
```

Then run:

```bash
.venv/bin/python scripts/check_eval_pdfs.py \
  --eval-dir unireg-eval \
  --report /tmp/unireg-eval-report.csv
```

The evaluation checks parser success, hierarchy counts, citation counts, and
whether parsed structure spans enough PDF pages to catch first-page-only
failures. It also reports normalized title metadata, extracted institution/code
values, and non-fatal title warnings.

## Metadata Normalization

Parser output keeps both normalized and raw title metadata:

```python
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("unireg-eval/university_a/학칙.pdf")
if result.document is None:
    raise RuntimeError("No document parsed")

regulation = result.document.regulation
print(regulation.title)
print(regulation.raw_title)
print(regulation.institution)
print(regulation.regulation_code)
```

## Export

```python
from unireg.exporters import JSONExporter, MarkdownExporter
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
if result.document is None:
    raise RuntimeError("No document parsed")

JSONExporter().dump(result.document, "out/regulation.json")
MarkdownExporter().dump(result.document, "out/regulation.md")
```

## Citations

```python
from unireg.citations import CitationGenerator
from unireg.parser import RegulationParser

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
citations = CitationGenerator().generate(result)

for citation in citations[:5]:
    print(citation.label, citation.source_label)
```

## Search and RAG Projections

```python
from unireg.parser import RegulationParser
from unireg.projections import ProjectionBuilder

result = RegulationParser().parse_file("examples/pdf/sample.pdf")
projection = ProjectionBuilder().build(result)

print(projection.bm25_documents[0].text)
print(projection.vector_documents[0].metadata)
print(projection.graph_edges[0].edge_type)
```

## UniRegBench

The local benchmark expects university samples under `unireg-eval/` and
currently includes parser/question fixtures for five `학칙.pdf` files:

- Dongduk Women's University
- Dongyang Mirae University
- Duksung Women's University
- Kwangwoon University
- Seoul Women's University

Validate the benchmark dataset:

```bash
.venv/bin/python scripts/unireg_benchmark.py validate --benchmark-dir benchmark
```

Run the reproducible parser/retrieval benchmark:

```bash
.venv/bin/python scripts/unireg_benchmark.py run \
  --benchmark-dir benchmark \
  --predictions benchmark/retrieval/predictions.sample.jsonl \
  --report-dir benchmark/reports
```

Reports are written as JSON, CSV, and Markdown.
Use `benchmark/retrieval/predictions.sample.jsonl` only as a reproducible
gold-first fixture; replace it with real retrieval output for experiments.

## Retrieval Evaluation

Run the deterministic BM25 baseline without using any LLM or external API:

```bash
.venv/bin/python scripts/unireg_retrieval.py bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl \
  --units article,clause,item,sub_item \
  --scope question_source \
  --top-k 5
```

The runner parses the benchmark source PDFs, builds article/clause/item/sub-item
retrieval units, ranks citations with BM25, and writes:

- `benchmark/retrieval/predictions.bm25.jsonl`
- `benchmark/reports/retrieval_bm25_report.json`
- `benchmark/reports/retrieval_bm25_questions.csv`
- `benchmark/reports/retrieval_bm25_hits.csv`

The default scope is `question_source`, which searches only the source file
identified by each benchmark question. Use `--scope corpus` to search across all
benchmark source files.

## Grounded QA

Run LLM-independent grounded QA with the deterministic MockLLM adapter:

```bash
.venv/bin/python scripts/unireg_qa.py \
  --question questions/example.txt \
  --retriever bm25 \
  --llm mock \
  --benchmark-dir benchmark \
  --output /tmp/unireg-qa-answer.json
```

Run QA over the benchmark questions:

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

The QA framework records a full trace for each answer:

```text
Question -> Retrieved Evidence -> Evidence Package -> LLM Input
-> Grounded Answer -> Evaluation
```

Benchmark QA writes:

- `benchmark/reports/qa_mock_report.json`
- `benchmark/reports/qa_mock_questions.csv`
- `benchmark/reports/qa_mock_answers.jsonl`

The MockLLM adapter does not call external APIs. Future OpenAI, Anthropic,
Gemini, or local adapters should consume the same Evidence Package contract.

## QA Error Analysis

Analyze benchmark QA traces to explain why each answer succeeded or failed:

```bash
.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

The same analyzer is available from the top-level CLI:

```bash
unireg analyze-errors \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis
```

The analyzer writes JSON, CSV, and Markdown reports with error taxonomy counts,
answerability breakdowns, retriever breakdowns, per-university summaries, top
failed questions, and representative examples.

## Experimental Evaluation

Run a reproducible offline experiment suite from a JSON config:

```bash
.venv/bin/python scripts/unireg_experiment.py run \
  --config experiments/configs/sample_offline.json
```

Aggregate one or more runs into a paper-style summary:

```bash
.venv/bin/python scripts/unireg_experiment.py summarize \
  --runs experiments/runs \
  --out experiments/reports/summary.md
```

The same commands are available through the top-level CLI:

```bash
unireg experiment run --config experiments/configs/sample_offline.json
unireg experiment summarize --runs experiments/runs --out experiments/reports/summary.md
```

Experiment runs write metadata, JSON results, CSV metrics, Markdown summaries,
and paper-style tables. The bundled sample config uses synthetic precomputed
fixtures only; it does not require private PDFs, API keys, external datasets, or
online LLM calls.
