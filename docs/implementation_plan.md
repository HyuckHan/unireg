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

Goal:

- Preserve appendices, supplementary provisions, forms, and table-like content.

Scope:

- `부칙`
- `[별표 n]`
- `【서식 제n호】`
- table placeholder nodes with raw text and source spans.

## Milestone 6: Reference and Incompleteness Detection

Goal:

- Preserve unresolved and missing references for grounded QA.

Scope:

- `세부사항은 따로 정한다`
- `총장이 따로 정한다`
- `별도 규정에 따른다`
- `시행세칙에 따른다`
- `Reference`
- `IncompletenessFlag`

## Milestone 7: Exporters

Goal:

- Provide stable Markdown and JSON outputs.

Scope:

- versioned JSON contract
- Markdown hierarchy export
- snapshot tests

## Milestone 8: Citation Layer

Goal:

- Generate deterministic citations from parsed nodes and source spans.

Scope:

- article citation
- clause citation
- item citation
- source page/file labels

## Milestone 9: Search and RAG Preparation

Goal:

- Build downstream projections without changing the canonical parser model.

Scope:

- BM25 documents
- vector documents
- graph nodes and edges
- missing-reference graph edges
