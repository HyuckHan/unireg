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

Goal:

- Build downstream projections without changing the canonical parser model.

Scope:

- BM25 documents
- vector documents
- graph nodes and edges
- missing-reference graph edges
