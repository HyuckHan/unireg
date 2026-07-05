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
