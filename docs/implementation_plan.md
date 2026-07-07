# Implementation Plan

This document records the implementation milestones for UniReg.

## Current Status

Completed:

- Phase 1 foundation
  - PDF loader
  - conservative cleaner
  - chapter parser
  - article parser
  - real PDF regression fixture
  - pytest and Ruff setup
- Core data model
  - hierarchy dataclasses
  - source spans
  - amendment/reference/incompleteness enums
  - JSON-compatible serialization
  - serialization round-trip tests
- Section parser
  - `제n절` heading detection
  - `Chapter -> Section -> Article` hierarchy
  - direct chapter articles still supported
- Clause parser
  - `①`, `②`, `③` clause marker detection
  - unnumbered clause fallback
  - article `body_lines` retained for migration compatibility
- Item and sub-item parser
  - `1.`, `2.`, `3.` item marker detection
  - `가.`, `나.`, `다.` sub-item marker detection
  - continuation lines attach to the last open item or sub-item
- Amendment and provision status
  - regulation effective/amendment date extraction
  - article amendment event extraction
  - deleted/repealed article status detection
- Appendix and table placeholders
  - `부칙`, `[별표 n]`, and `【서식 제n호】` detection
  - appendix-level raw text preservation
  - table placeholder nodes for annex table content
- Reference and incompleteness detection
  - unresolved implicit references
  - missing internal regulation references
  - administrative-discretion references
  - node-level incompleteness flags
- Exporters
  - versioned JSON export
  - Markdown hierarchy export
  - exporter snapshot tests
- Citation layer
  - article, clause, item, and sub-item citations
  - deterministic citation labels
  - source file/page labels
  - citation serialization tests
- Cross-university evaluation harness
  - local `unireg-eval` corpus layout
  - university-level PDF smoke evaluation
  - source page coverage checks
  - CSV report output
- Benchmark, retrieval, QA, and error analysis
  - UniRegBench parser/question fixtures
  - deterministic BM25 retrieval baseline
  - LLM-independent grounded QA with MockLLM
  - traceable QA answer JSONL
  - deterministic multi-label QA error analysis
- Experimental evaluation
  - JSON experiment configs
  - reproducible run metadata
  - parser/retrieval/QA/missing-regulation/cross-university experiments
  - paper-style JSON, CSV, and Markdown outputs
  - aggregate experiment summaries

## Milestone 1: Section Parser

Status: implemented.

Goal:

- Add optional `Section` support between `Chapter` and `Article`.

Scope:

- Detect Korean section headings such as `제1절 통칙`.
- Preserve both forms:
  - `Chapter -> Article`
  - `Chapter -> Section -> Article`
- Attach article metadata:
  - regulation title
  - chapter title
  - section title, when present
- Preserve source spans.
- Keep clause parsing out of scope.

Tests:

- section heading pattern test
- chapter with direct articles only
- chapter with sections and section-contained articles
- chapter containing a direct article before a section
- serialization includes `sections`

Completion criteria:

- Existing real PDF regression still passes.
- Section fixture parses into `Chapter.sections`.
- `pytest` passes.
- `ruff check` passes.

## Milestone 2: Clause Parser

Status: implemented.

Goal:

- Parse `①`, `②`, `③` clause markers under articles.

Scope:

- Numbered clauses.
- Unnumbered article body fallback.
- Source span preservation.
- Article body compatibility during migration.

Out of scope:

- Item parsing.
- Sub-item parsing.
- Amendment/reference enrichment.

## Milestone 3: Item and SubItem Parser

Status: implemented.

Goal:

- Parse item and sub-item hierarchy under clauses.

Scope:

- `1.`, `2.`, `3.` item markers.
- `가.`, `나.`, `다.` sub-item markers.
- PDF-attached marker splitting.
- Item/sub-item source spans.

## Milestone 4: Amendment and Provision Status

Status: implemented.

Goal:

- Preserve amendment history and provision status.

Scope:

- `<개정 ...>`
- `<신설 ...>`
- `[본조신설 ...]`
- `삭제`
- repealed/deleted status markers.

Tests:

- regulation title effective and amendment dates
- article-level amendment history events
- deleted and repealed article statuses
- real PDF first article amendment regression

## Milestone 5: Appendix and Table Placeholders

Status: implemented.

Goal:

- Preserve appendices, supplementary provisions, forms, and table-like content.

Scope:

- `부칙`
- `[별표 n]`
- `【서식 제n호】`
- table placeholder nodes with raw text and source spans.

Tests:

- appendix and table heading pattern tests
- parser fixture for supplementary provisions, annexes, forms, and tables
- serialization round-trip for appendix/table nodes
- real PDF appendix/table regression

## Milestone 6: Reference and Incompleteness Detection

Status: implemented.

Goal:

- Preserve unresolved and missing references for grounded QA.

Scope:

- `세부사항은 따로 정한다`
- `총장이 따로 정한다`
- `별도 규정에 따른다`
- `시행세칙에 따른다`
- `Reference`
- `IncompletenessFlag`

Tests:

- reference pattern detection
- missing regulation and unresolved-reference status mapping
- administrative-discretion flagging
- item/sub-item reference attachment
- parser output serialization with reference metadata

## Milestone 7: Exporters

Status: implemented.

Goal:

- Provide stable Markdown and JSON outputs.

Scope:

- versioned JSON contract
- Markdown hierarchy export
- snapshot tests

Tests:

- JSON exporter versioned payload snapshot
- JSON exporter round-trip load
- Markdown hierarchy snapshot
- empty parse result export guard

## Milestone 8: Citation Layer

Status: implemented.

Goal:

- Generate deterministic citations from parsed nodes and source spans.

Scope:

- article citation
- clause citation
- item citation
- source page/file labels

Tests:

- deterministic article/clause/item/sub-item labels
- source page label generation
- citation serialization round-trip
- empty parse result citation guard

## Milestone 8.5: Cross-University Evaluation Harness

Status: implemented.

Goal:

- Test parser robustness against external university regulation samples before
  building search and RAG projections.

Scope:

- Evaluate PDFs under `unireg-eval/<university>/`.
- Report university name, parser status, article/clause/item counts, citation
  count, PDF page count, and structural source-page coverage.
- Emit optional CSV reports.
- Keep evaluation PDFs local and ignored by git.

Tests:

- page span coverage helpers
- university folder name detection
- threshold failure messages
- page range formatting

Usage:

```bash
.venv/bin/python scripts/check_eval_pdfs.py \
  --eval-dir unireg-eval \
  --report /tmp/unireg-eval-report.csv
```

Current external evaluation result:

```text
total=5 ok=5 failed=0
```

## Milestone 9: Metadata and Title Normalization

Status: implemented.

Goal:

- Normalize regulation metadata before search and RAG document generation.

Motivation:

- Cross-university evaluation showed that structure parsing is broadly stable,
  but some PDFs merge regulation title, regulation code, amendment history, and
  first chapter text into one noisy title.
- Search/RAG documents should not inherit noisy metadata.

Scope:

- Split raw title candidates from normalized regulation title.
- Extract institution name when it is available from filename, folder profile,
  or document text.
- Normalize regulation codes such as `[2-0-1]`.
- Separate enactment/amendment metadata from regulation title when it appears
  inline.
- Preserve the original raw title text for traceability.
- Add external evaluation checks that flag suspicious titles.

Out of scope:

- Corpus-level reference resolution.
- Vector DB document generation.
- Institution-specific parser plugins.

Tests:

- title normalization fixtures for current five external universities
- noisy title regression for PDFs where first chapter text is attached
- serialization preserves both raw and normalized metadata
- evaluation script reports title warnings without failing structural parsing

Implemented behavior:

- `Regulation.title` now stores the normalized title.
- `Regulation.raw_title` preserves the original source title candidate.
- `Regulation.title_candidates` preserves intermediate normalization candidates.
- `Regulation.regulation_code` stores extracted catalog codes.
- `Regulation.institution` is extracted conservatively when the source contains
  an institution-level name such as `대학교`.
- Evaluation reports include normalized title, raw title, institution,
  regulation code, and metadata warning codes.

## Milestone 10: Search and RAG Preparation

Status: implemented.

Goal:

- Build downstream projections without changing the canonical parser model.

Scope:

- BM25 documents
- vector documents
- graph nodes and edges
- missing-reference graph edges

Implemented behavior:

- `ProjectionBuilder` builds downstream projections from `ParseResult`,
  `RegulationDocument`, or `Regulation`.
- `BM25Document` preserves searchable text, citation labels, source labels, and
  string metadata.
- `VectorDocument` preserves vector-DB-ready chunks with the same citation and
  metadata contract.
- `GraphNode` and `GraphEdge` preserve hierarchy and reference graph structure.
- Missing or unresolved regulation references become graph edges with
  `target_node_id=None` and missing-target metadata in edge properties.

Tests:

- search/vector document generation
- hierarchy graph edge generation
- missing-reference graph edge generation
- projection serialization round-trip
- empty parse result guard

## Milestone 11: UniRegBench

Status: implemented.

Goal:

- Create the canonical reproducible benchmark dataset and evaluation CLI for
  parser and retrieval outputs.

Scope:

- benchmark directory layout
- JSONL question schema
- parser benchmark case schema
- retrieval prediction schema
- benchmark loader
- benchmark validation
- parser evaluation
- retrieval metric evaluation
- JSON, CSV, and Markdown reports

Implemented behavior:

- `benchmark/` contains stable question, parser, retrieval, QA, and reports
  directories.
- `unireg.benchmark` exposes dataclasses, loaders, validation, evaluation, and
  report writers.
- `scripts/unireg_benchmark.py` and `python -m unireg.benchmark` provide a
  usable CLI.
- `unireg-benchmark` is available as a package console script after install.
- Retrieval evaluation supports Recall@1, Recall@3, Recall@5, and MRR.
- Parser evaluation reports article extraction, clause extraction, hierarchy,
  citation, and metadata scores.
- The local benchmark dataset covers five university `학칙.pdf` files under
  `unireg-eval/`.
- University-specific questions include `source_file` in gold citations so
  retrieval evaluation disambiguates identical article numbers across
  institutions.
- Parser cases use reviewed structural thresholds and required citations rather
  than exact chapter counts while inline chapter heading handling remains a
  known parser robustness issue.

Reproducible run:

```bash
.venv/bin/python scripts/unireg_benchmark.py run \
  --benchmark-dir benchmark \
  --predictions benchmark/retrieval/predictions.sample.jsonl \
  --report-dir benchmark/reports
```

## Milestone 12: Retrieval Evaluation

Status: implemented.

Goal:

- Evaluate retrieval quality independently from LLMs.

Scope:

- deterministic BM25 baseline
- retrieval runner over UniRegBench questions
- article, clause, item, and sub-item retrieval units
- Recall@1, Recall@3, Recall@5, MRR, and nDCG@5
- JSONL prediction output
- JSON and CSV reports

Implemented behavior:

- `unireg.retrieval` provides BM25 indexing, retrieval corpus construction,
  benchmark execution, report writing, and CLI entry points.
- Retrieval units are built from existing `ProjectionBuilder` BM25 documents;
  the parser is unchanged.
- `scripts/unireg_retrieval.py`, `python -m unireg.retrieval`, and the
  `unireg-retrieval` console script run the deterministic BM25 baseline.
- Retrieval evaluation uses hierarchical citation matching so article-level and
  fine-grained units can be evaluated together.
- Generated BM25 predictions are ignored by git while the benchmark fixtures
  remain versioned.

Reproducible run:

```bash
.venv/bin/python scripts/unireg_retrieval.py bm25 \
  --benchmark-dir benchmark \
  --report-dir benchmark/reports \
  --predictions benchmark/retrieval/predictions.bm25.jsonl \
  --units article,clause,item,sub_item \
  --scope question_source \
  --top-k 5
```

Current local five-university result:

```text
questions=20
documents=2316
Recall@1=0.700
Recall@3=1.000
Recall@5=1.000
MRR=0.842
nDCG@5=0.883
```

## Milestone 13: Grounded QA Framework

Status: implemented.

Goal:

- Build an LLM-independent grounded QA framework on top of retrieval.

Scope:

- QA pipeline
- Evidence Package
- abstract LLM adapter
- deterministic MockLLM adapter
- Grounded Answer schema
- hallucination guardrails
- QA evaluation metrics
- single-question and benchmark CLI
- traceable JSON/CSV/JSONL reports

Implemented behavior:

- `unireg.qa` owns the QA pipeline without changing parser or retrieval
  architecture.
- The Evidence Package stores retrieved nodes, citations, source pages,
  metadata, incompleteness flags, scores, and normalized confidence.
- `LLMAdapter` defines the provider boundary; only `MockLLMAdapter` is
  implemented.
- `GroundedAnswer` stores answer text, citations, evidence, completeness status,
  confidence, reasoning metadata, exact LLM input, raw LLM output, guardrail
  events, and optional evaluation.
- Guardrails remove unsupported citations, force unknown answers when evidence
  is absent, and downgrade complete answers without supported citations.
- QA reports allow reconstructing
  `Question -> Retrieved Evidence -> LLM Input -> Grounded Answer -> Evaluation`
  without ambiguity.

Benchmark run:

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

Current local five-university MockLLM result:

```text
questions=20
citation_accuracy=0.700
groundedness=1.000
completeness_classification=0.800
hallucination_rate=0.000
```

## Milestone 13.5: Explainability and Error Analysis

Status: implemented.

Goal:

- Explain why each grounded QA result succeeded or failed.

Scope:

- Consume Milestone 13 QA answer trace JSONL.
- Enrich older traces with benchmark answerability labels and gold citations
  when needed.
- Classify failures with a deterministic multi-label error taxonomy.
- Produce JSON, CSV, and Markdown reports.
- Report aggregate success/failure counts, error distributions,
  answerability/retriever/university breakdowns, top failed questions, and
  representative examples.

Implemented behavior:

- `unireg.analysis` owns trace loading, classification, aggregation, report
  writing, and CLI entry points.
- The parser and retrieval architectures are unchanged.
- The QA evaluation row now includes `answerability` and `gold_citations` so new
  QA traces are self-contained for later analysis.
- `scripts/unireg_analyze_errors.py`, `python -m unireg.analysis`, the
  `unireg-error-analysis` console script, and `unireg analyze-errors` all run
  the analyzer.

Reproducible run:

```bash
.venv/bin/python scripts/unireg_analyze_errors.py \
  --traces benchmark/reports/qa_mock_answers.jsonl \
  --out benchmark/reports/error_analysis \
  --benchmark-dir benchmark
```

## Milestone 14: Experimental Evaluation

Status: implemented.

Goal:

- Make UniReg experiments reproducible, comparable, and publication-ready.

Scope:

- `unireg.experiments` package
- JSON config loader and validator
- experiment runner
- run metadata
- parser, retrieval, QA, missing-regulation, and cross-university experiment
  orchestration
- JSON/CSV/Markdown outputs
- paper-style table generation
- multi-run summarizer
- synthetic offline fixtures for CI-safe tests

Implemented CLI:

```bash
.venv/bin/python scripts/unireg_experiment.py run \
  --config experiments/configs/sample_offline.json

.venv/bin/python scripts/unireg_experiment.py summarize \
  --runs experiments/runs \
  --out experiments/reports/summary.md
```
