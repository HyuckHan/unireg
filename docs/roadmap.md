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

## Phase 2

- Reference resolution
  - Corpus-level reference matching
  - Missing internal rule confirmation
  - Unknown external rule classification
- Answerability handling
  - Answerability status model
  - Missing-source preservation
  - Graph edge preparation

## Phase 3

- JSON schema publication
- Export compatibility tests across schema versions
- CLI export commands

## Phase 4

- Citation support
- Source span citation
- Article, clause, and item-level citation
- Citation validation tests

## Phase 5

- Knowledge graph
- Reference graph
- Missing-reference graph edges
- Regulation-to-regulation links

## Phase 6

- Search engine
  - BM25
  - Metadata-aware filtering
  - Hierarchy-aware result grouping

## Phase 7

- Vector database
- Embedding chunk strategy
- Article, clause, and item chunks
- Metadata preservation

## Phase 8

- RAG
- Hybrid retrieval
- Grounded answer generation
- Answer completeness classification
- Missing-regulation reporting

## Phase 9

- Web UI
- Regulation browser
- Search interface
- Citation display
- Missing-reference display

## Phase 10

- Multi-university support
- Institution metadata
- Source collection profiles
- Parser configuration by institution
