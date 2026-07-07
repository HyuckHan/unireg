# UniRegBench

UniRegBench is the reproducible benchmark dataset for UniReg.

Directory layout:

```text
benchmark/
  questions/
  retrieval/
  qa/
  parser/
  reports/
```

The current local benchmark covers five university `학칙.pdf` files under
`unireg-eval/`:

- `university_dongduk`
- `university_dongyang`
- `university_duksung`
- `university_kwangwoon`
- `university_seoulwomen`

The PDFs are local evaluation inputs and are intentionally ignored by git.
Keep the same directory names when running this benchmark on another machine.

First run the external PDF smoke test:

```bash
.venv/bin/python scripts/check_eval_pdfs.py \
  --eval-dir unireg-eval \
  --report /tmp/unireg-eval-report.csv
```

Run validation:

```bash
.venv/bin/python scripts/unireg_benchmark.py validate --benchmark-dir benchmark
```

Run the reproducible benchmark:

```bash
.venv/bin/python scripts/unireg_benchmark.py run \
  --benchmark-dir benchmark \
  --predictions benchmark/retrieval/predictions.sample.jsonl \
  --report-dir benchmark/reports
```

Generated reports are written as JSON, CSV, and Markdown under
`benchmark/reports`.

The sample retrieval prediction file is a gold-first reproducibility fixture.
Replace `benchmark/retrieval/predictions.sample.jsonl` with real retrieval
outputs when evaluating a search or RAG system.

Run the BM25 retrieval baseline:

```bash
.venv/bin/python scripts/unireg_retrieval.py bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl \
  --units article,clause,item,sub_item \
  --scope question_source \
  --top-k 5
```

This generates ranked predictions plus JSON/CSV retrieval reports. The generated
BM25 prediction file is ignored by git.

Run grounded QA with the deterministic MockLLM adapter:

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

The QA answers JSONL contains the full trace for each benchmark question:

```text
question -> retrieved evidence -> LLM input -> grounded answer -> evaluation
```

Analyze QA failures for publication-oriented error analysis:

```bash
.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

The error analyzer writes:

- `benchmark/reports/error_analysis/error_analysis.json`
- `benchmark/reports/error_analysis/error_analysis.csv`
- `benchmark/reports/error_analysis/error_analysis.md`
