# Milestone 11: UniRegBench

Status: Implemented

## Goal

Create the official benchmark dataset for UniReg.

This benchmark will be used to evaluate

- Parser
- Retrieval
- Grounded QA
- Future LLMs

The benchmark becomes the canonical evaluation suite of the project.

---

## Motivation

The parser is now considered feature-complete.

The next phase is not adding more parser features.

Instead, we must establish a reproducible evaluation framework.

The benchmark should remain stable while parser and retrieval
implementations evolve.

---

## Directory Layout

benchmark/

    questions/

    retrieval/

    qa/

    parser/

    reports/

The implemented layout also stores JSON schema files next to the JSONL files
they validate:

- `benchmark/questions/questions.schema.json`
- `benchmark/parser/parser_cases.schema.json`
- `benchmark/retrieval/predictions.schema.json`

---

## Question Format

Each question should be stored as JSONL.

Example

{
    "id":"Q0001",
    "question":"휴학은 최대 몇 학기 가능한가?",
    "answerability":"answerable",
    "gold_citations":[
        {
            "article":"제25조",
            "clause":"①"
        }
    ]
}

---

## Answerability Types

- answerable
- partially_answerable
- missing_regulation
- unanswerable
- comparison
- multi_hop

---

## Parser Evaluation

Measure

- article extraction accuracy
- clause extraction accuracy
- hierarchy preservation
- citation generation
- metadata completeness

---

## Retrieval Evaluation

Support

- Recall@1
- Recall@3
- Recall@5
- MRR

---

## Output

CSV

JSON

Markdown report

---

## Deliverables

- benchmark schema
- benchmark loader
- validation
- evaluation CLI

## Implemented CLI

Validate the benchmark:

```bash
.venv/bin/python scripts/unireg_benchmark.py validate --benchmark-dir benchmark
```

Run parser and retrieval evaluation with the reproducible sample predictions:

```bash
.venv/bin/python scripts/unireg_benchmark.py run \
  --benchmark-dir benchmark \
  --predictions benchmark/retrieval/predictions.sample.jsonl \
  --report-dir benchmark/reports
```

The same CLI can be run as a module:

```bash
.venv/bin/python -m unireg.benchmark validate --benchmark-dir benchmark
```

When the package is installed, the console script is:

```bash
unireg-benchmark validate --benchmark-dir benchmark
```

## Implemented Reports

The CLI writes:

- `benchmark_report.json`
- `benchmark_report.md`
- `parser_report.csv`
- `retrieval_report.csv`

Generated report files are ignored by git so benchmark runs are reproducible
without committing machine-local output.

## Current Local Dataset

The benchmark fixtures now cover five local `학칙.pdf` files:

- `unireg-eval/university_dongduk/학칙.pdf`
- `unireg-eval/university_dongyang/학칙.pdf`
- `unireg-eval/university_duksung/학칙.pdf`
- `unireg-eval/university_kwangwoon/학칙.pdf`
- `unireg-eval/university_seoulwomen/학칙.pdf`

The PDFs are local evaluation inputs and are ignored by git. Parser cases use
reviewed structural thresholds plus required citations instead of exact chapter
counts because some PDFs attach chapter headings inline with article text.

Question gold citations include `source_file` so the retrieval benchmark can
distinguish the same article number across different universities.
