# Roadmap

## Phase 1

- Project skeleton
  - Python package layout
  - Ruff, Black, mypy or pyright, pytest
  - CI-ready test command
- Core data model
  - Regulation
  - Chapter
  - Section
  - Article
  - Clause
  - Item
  - Sub-item
  - Source span
  - Amendment metadata
  - Reference and incompleteness enums
- Golden fixtures
  - Minimal Korean regulation examples
  - Realistic PDF-extracted text examples
  - Expected JSON snapshots
- Text extraction interface
  - PDF extraction
  - Page number preservation
  - Source file preservation
  - HWP adapter boundary
- Document cleaner
  - Whitespace normalization
  - Page header/footer handling
  - Page break preservation
- Hierarchy parser
  - Chapter parser
  - Section parser
  - Article parser
  - Clause parser
  - Item parser
  - Sub-item parser
  - Appendix parser
  - Table placeholder parser
- Metadata enrichment
  - Repealed provisions
  - Newly inserted provisions
  - Effective dates
  - Reference detection
  - Incompleteness flagging
- Parser validation
  - Hierarchy preservation tests
  - Source metadata tests
  - Malformed input tests
- Exporters
  - Markdown hierarchy export
  - JSON export
  - Round-trip/snapshot tests
- Citations
  - Source span citation labels
  - Article, clause, item, and sub-item citation projections
  - Citation serialization tests
- Cross-university evaluation
  - Local `unireg-eval` corpus layout
  - Per-university PDF smoke evaluation
  - Source page coverage reporting
  - CSV evaluation reports

## Phase 2

- Metadata and title normalization
  - Raw title preservation
  - Normalized regulation title
  - Institution metadata extraction
  - Regulation code extraction
  - Inline amendment metadata cleanup
  - Suspicious title warnings in evaluation reports

## Phase 3

- UniRegBench
  - Benchmark schema
  - Benchmark loader and validation
  - University-specific parser and question fixtures
  - Gold citations scoped by source file
  - Parser evaluation reports
  - Retrieval metrics for supplied predictions
  - Reproducible benchmark CLI

## Phase 4

- Retrieval evaluation
  - BM25 baseline
  - Article, clause, item, and sub-item retrieval units
  - Recall@1, Recall@3, Recall@5, MRR, and nDCG@5
  - Prediction JSONL output
  - Retrieval CSV/JSON reports

## Phase 5

- Grounded QA framework
  - Evidence Package
  - abstract LLM adapter
  - MockLLM adapter
  - Grounded Answer schema
  - hallucination guardrails
  - citation accuracy, groundedness, completeness, hallucination metrics
  - traceable QA reports
- Explainability and error analysis
  - QA trace ingestion
  - deterministic multi-label error taxonomy
  - JSON, CSV, and Markdown error reports
  - answerability, retriever, and university breakdowns
  - representative failure examples for paper analysis
- Experimental evaluation
  - JSON experiment configs
  - reproducible run metadata
  - parser, retrieval, QA, missing-regulation, and cross-university experiment
    orchestration
  - paper-style result tables
  - aggregate run summaries

## Phase 6

- Reference resolution
  - Corpus-level reference matching
  - Missing internal rule confirmation
  - Unknown external rule classification
- Answerability handling
  - Answerability status model
  - Missing-source preservation
  - Graph edge preparation

## Phase 7

- JSON schema publication
- Export compatibility tests across schema versions
- CLI export commands

## Phase 8

- Citation compatibility validation
- Citation display integration
- Citation checks against source text hashes

## Phase 9

- Knowledge graph
- Reference graph
- Missing-reference graph edges
- Regulation-to-regulation links

## Phase 10

- Search engine
  - BM25
  - Metadata-aware filtering
  - Hierarchy-aware result grouping

## Phase 11

- Vector database
- Embedding chunk strategy
- Article, clause, and item chunks
- Metadata preservation

## Phase 12

- RAG
- Hybrid retrieval
- Grounded answer generation
- Answer completeness classification
- Missing-regulation reporting

## Phase 13

- Web UI
- Regulation browser
- Search interface
- Citation display
- Missing-reference display

## Phase 14

- Multi-university support
- Institution metadata
- Source collection profiles
- Parser configuration by institution
