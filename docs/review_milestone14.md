# Milestone 14 Review: Experimental Evaluation

## What Was Implemented

Milestone 14 added a reproducible experimental evaluation suite for UniReg.

Implemented components:

- `unireg.experiments` package.
- JSON experiment config loader and validator.
- Experiment runner that orchestrates existing parser, retrieval, QA, and error
  analysis components.
- Reproducibility metadata generation.
- JSON, CSV, and Markdown run outputs.
- Paper-style table writers.
- Multi-run summarizer.
- CLI entry points:
  - `scripts/unireg_experiment.py`
  - `python -m unireg.experiments`
  - `unireg-experiment`
  - `unireg experiment`
- Synthetic offline fixtures under `experiments/fixtures/sample`.
- Sample config:
  - `experiments/configs/sample_offline.json`
- pytest coverage for config loading, validation, runner output, metadata,
  unavailable metrics, deterministic sample runs, aggregation, missing inputs,
  and the no-online-LLM default.

## Experiment Architecture

The experiment layer is an orchestrator.

It does not modify parser, retrieval, or QA architecture. Instead, it calls the
existing components built in earlier milestones:

- parser benchmark evaluation from Milestone 11
- BM25 retrieval evaluation from Milestone 12
- grounded QA with `MockLLM` from Milestone 13
- error analysis from Milestone 13.5
- cross-university PDF evaluation harness when local PDFs are available

The runner supports two modes:

- `run`
  - Execute an existing UniReg pipeline component.
- `precomputed`
  - Read saved artifacts and produce the same experiment reports.

The precomputed mode is important for CI and paper artifact checks because the
repository cannot include private PDFs or copyrighted university regulations.

## Supported Experiment Types

Supported experiment types:

- `parser_accuracy`
- `retrieval`
- `grounded_qa`
- `missing_regulation`
- `cross_university`

Only BM25 retrieval and MockLLM QA are supported by default. Dense retrieval,
hybrid retrieval, hierarchical retrieval, and online LLM providers are left for
future milestones unless their outputs are supplied as compatible precomputed
artifacts.

## Output Formats

Each experiment run writes:

- `result.json`
- `metadata.json`
- `metrics.csv`
- `summary.md`
- `tables/*.csv`
- `tables/*.md`
- `artifacts/`

The standard paper tables are:

- `parser_results_by_university`
- `retrieval_method_comparison`
- `qa_results_by_answerability`
- `missing_regulation_error_analysis`
- `error_category_distribution`
- `cross_university_generalization`

The aggregate command writes:

- `summary.md`
- `summary.json`
- `summary.csv`

## Reproducibility Guarantees

Every run records:

- timestamp
- config path
- project version
- git commit hash
- Python version
- platform
- input paths
- output paths
- random seed
- command-line arguments

The synthetic sample experiment is deterministic and uses only committed
fixtures. It requires no external APIs, no online LLM calls, no external
datasets, and no private PDFs.

## Known Limitations

- JSON configs are supported; YAML configs are not implemented to avoid adding a
  dependency.
- The runner supports BM25 and MockLLM only as executable methods.
- Dense, hybrid, hierarchical retrieval, and online LLM comparisons require
  future method implementations or precomputed compatible artifacts.
- Parser warnings are marked unavailable when the parser benchmark artifact does
  not expose warning counts.
- The sample fixtures are synthetic and only validate the experiment framework,
  not real parser quality.
- Cross-university run mode still depends on local PDFs under a user-provided
  corpus directory.
- Figures are represented by the output layout but no plotting is implemented.
- The current benchmark remains small, so paper conclusions require expanded
  human-reviewed data.

## How To Add A New Experiment

1. Add a config under `experiments/configs`.
2. Select one or more `experiment_types`.
3. Choose `run` mode when the local corpus and benchmark inputs are available.
4. Choose `precomputed` mode when publishing or testing from saved artifacts.
5. Run:

```bash
unireg experiment run --config experiments/configs/<config>.json
```

To add a new method, wire it into `unireg.experiments.runner` by converting the
method output into the existing metric and table records. The method should not
change parser, retrieval, or QA contracts.

## How To Reproduce Paper Tables

Run one or more experiment configs:

```bash
unireg experiment run --config experiments/configs/sample_offline.json
```

Aggregate all runs:

```bash
unireg experiment summarize \
  --runs experiments/runs \
  --out experiments/reports/summary.md
```

The aggregate summary includes metrics and merged paper tables. Each table row
can be traced back to a run `result.json`, which contains the config, metadata,
raw results, metrics, artifacts, and generated tables.

## Recommendations For The Next Milestone

- Expand UniRegBench with more manually verified questions and held-out
  universities.
- Add experiment configs for retrieval ablations:
  - article only
  - clause only
  - article plus clause
  - article plus clause plus item plus sub-item
- Add corpus-scope retrieval and QA configs for cross-university
  disambiguation.
- Add schema files for experiment configs and run results.
- Add figure generation only after paper table definitions are stable.
- Add local deterministic LLM evaluation only if the environment and model
  artifact policy are reproducible.
- Keep online provider experiments separate until API policy, caching, and
  reproducibility constraints are explicit.
