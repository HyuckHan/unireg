# Milestone 14: Experimental Evaluation

Status: Implemented

## Goal

Build a reproducible experimental evaluation suite for UniReg.

The experiment layer orchestrates existing parser, retrieval, grounded QA, and
error-analysis components. It does not introduce parser features, new retrieval
algorithms, online LLM inference, external APIs, or external datasets.

## Directory Layout

```text
experiments/
  configs/
  fixtures/
  runs/
  reports/
  tables/
  figures/
  scripts/
```

Generated outputs under `experiments/runs`, `experiments/reports`,
`experiments/tables`, and `experiments/figures` are ignored by git. Configs and
synthetic fixtures are versioned.

## Configuration

Milestone 14 supports JSON experiment configs.

Example:

```bash
experiments/configs/sample_offline.json
```

Each config records:

- experiment name
- experiment types
- corpus location
- benchmark directory
- benchmark question file
- parser output location
- retrieval method
- QA method
- evaluation metrics
- output directory
- random seed
- notes
- tags
- per-experiment mode and input artifacts

Relative paths are resolved from the config file location.

Supported execution modes:

- `run`
  - Execute existing UniReg benchmark, BM25, QA, or cross-university components.
- `precomputed`
  - Read saved JSON/CSV/JSONL artifacts and generate the same experiment
    reports. This is used by CI-safe synthetic fixtures.

## CLI

Run one experiment:

```bash
.venv/bin/python scripts/unireg_experiment.py run \
  --config experiments/configs/sample_offline.json
```

Aggregate runs:

```bash
.venv/bin/python scripts/unireg_experiment.py summarize \
  --runs experiments/runs \
  --out experiments/reports/summary.md
```

Top-level CLI:

```bash
unireg experiment run --config experiments/configs/sample_offline.json
unireg experiment summarize --runs experiments/runs --out experiments/reports/summary.md
```

Installed console script:

```bash
unireg-experiment run --config experiments/configs/sample_offline.json
```

## Supported Experiment Types

### Experiment 1: Parser Accuracy

Uses the existing benchmark parser evaluation.

Reported metrics:

- article extraction accuracy
- clause extraction accuracy
- hierarchy preservation
- citation/source-span coverage through citation generation
- metadata completeness
- parser warnings as unavailable when the source artifact does not expose them

Output table:

- `parser_results_by_university`

### Experiment 2: Retrieval Evaluation

Uses the Milestone 12 BM25 retrieval runner or precomputed BM25 report.

Reported metrics:

- Recall@1
- Recall@3
- Recall@5
- MRR
- nDCG@5

Output table:

- `retrieval_method_comparison`

Dense, hybrid, and hierarchical retrieval are not implemented in this milestone.
Future methods should emit comparable artifacts and be wired into the experiment
runner without changing the parser or QA contracts.

### Experiment 3: Grounded QA Evaluation

Uses the Milestone 13 grounded QA framework with deterministic `MockLLM`.

Reported metrics:

- citation accuracy
- groundedness
- hallucination rate
- completeness classification accuracy
- answerability breakdown

Output table:

- `qa_results_by_answerability`

Online LLM providers are not required and are not called.

### Experiment 4: Missing Regulation / Incompleteness

Uses Milestone 13.5 error analysis over QA traces.

Reported metrics:

- missing regulation detection accuracy
- hallucination under incomplete evidence
- completeness misclassification count
- unsupported answer count

Output tables:

- `missing_regulation_error_analysis`
- `error_category_distribution`

### Experiment 5: Cross-University Generalization

Uses either precomputed cross-university CSV reports or the existing
cross-university PDF evaluation harness when local PDFs are available.

Reported metrics:

- parse success rate
- average page coverage
- university count

Output table:

- `cross_university_generalization`

Structural parser evaluation is kept separate from retrieval and QA evaluation.
The runner does not assume every university has QA labels.

## Run Metadata

Every run writes `metadata.json` with:

- timestamp
- config path
- project version
- git commit hash, if available
- Python version
- platform
- input dataset paths
- output paths
- random seed
- command-line arguments

## Outputs

Each run writes:

- `result.json`
- `metadata.json`
- `metrics.csv`
- `summary.md`
- `tables/*.csv`
- `tables/*.md`
- generated or consumed artifacts under `artifacts/`

Aggregated summaries write:

- `summary.md`
- `summary.json`
- `summary.csv`

## Reproducible Sample

The bundled sample config is deterministic and offline:

```bash
.venv/bin/python scripts/unireg_experiment.py run \
  --config experiments/configs/sample_offline.json

.venv/bin/python scripts/unireg_experiment.py summarize \
  --runs experiments/runs \
  --out experiments/reports/summary.md
```

The sample uses synthetic JSON, CSV, and JSONL fixtures under
`experiments/fixtures/sample`. It does not commit PDFs, copyrighted source
documents, API keys, or external datasets.

## Traceability

Every reported number is traceable through:

```text
Config
  -> Input data
  -> System output or precomputed artifact
  -> Evaluation metric
  -> Report table
```

The saved `result.json` binds all metrics, tables, raw results, artifacts, run
metadata, and the normalized config.
