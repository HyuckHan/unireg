# Parser Design

This document designs the regulation parser architecture. It is not an
implementation plan for RAG, search, graph storage, or a web UI.

The parser's job is to transform extracted regulation text into the canonical
data model described in `docs/data_model.md`.

## Goals

- Preserve legal hierarchy:
  `Regulation -> Chapter -> Section -> Article -> Clause -> Item -> SubItem`.
- Preserve source provenance for citations.
- Parse partially damaged extraction output without silently flattening legal
  structure.
- Surface parser uncertainty as diagnostics.
- Keep parser modules deterministic and testable.
- Make PDF and HWP extraction replaceable behind interfaces.

## Non-goals

- Do not embed graph database logic in the parser.
- Do not embed vector database logic in the parser.
- Do not call LLMs during deterministic parsing.
- Do not treat the parser output as plain chunks.
- Do not invent referenced regulations when source documents are missing.

## Parser Pipeline

```text
Input file
  |
  v
Text extraction
  |
  v
Source-preserving document representation
  |
  v
Document cleaning
  |
  v
Line/block classification
  |
  v
Hierarchy parsing
  |
  v
Metadata enrichment
  |
  v
Validation and diagnostics
  |
  v
RegulationDocument
```

### 1. Text Extraction

Text extraction converts source files into page-aware text records.

Responsibilities:

- Read PDF initially.
- Leave an HWP adapter boundary for future support.
- Preserve source file path.
- Preserve page numbers.
- Preserve raw text.
- Preserve enough offsets to map parsed nodes back to source text.

Output concept:

```python
class TextExtractor(Protocol):
    def extract(self, source_file: Path) -> ExtractedDocument:
        ...
```

The extractor should not classify legal structure. It only extracts text and
source coordinates.

### 2. Source-Preserving Document Representation

The parser should operate on an intermediate representation rather than raw
strings.

Conceptual records:

```python
@dataclass(slots=True, kw_only=True)
class ExtractedDocument:
    source_file: str
    pages: list[ExtractedPage]
    extraction_method: str


@dataclass(slots=True, kw_only=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(slots=True, kw_only=True)
class SourceLine:
    text: str
    source_span: SourceSpan
    line_number: int
```

The exact implementation can evolve, but every downstream stage must keep
`SourceSpan` available.

### 3. Document Cleaning

The cleaner normalizes extracted text while preserving source mapping.

Responsibilities:

- Normalize Unicode compatibility variants when safe.
- Normalize whitespace.
- Join broken lines only when there is a strong rule.
- Remove repeated headers and footers only when confidently detected.
- Preserve page breaks.
- Preserve original raw lines for diagnostics.

The cleaner should produce clean lines, not legal nodes.

Interface:

```python
class DocumentCleaner(Protocol):
    def clean(self, document: ExtractedDocument) -> CleanDocument:
        ...
```

Cleaning rules must be conservative. A suspicious line should remain available
for classification rather than being discarded.

### 4. Line and Block Classification

The classifier labels each clean line with a structural role.

Expected token kinds:

- `REGULATION_TITLE`
- `CHAPTER_HEADING`
- `SECTION_HEADING`
- `ARTICLE_HEADING`
- `CLAUSE_MARKER`
- `ITEM_MARKER`
- `SUB_ITEM_MARKER`
- `APPENDIX_HEADING`
- `TABLE_START`
- `AMENDMENT_NOTE`
- `EFFECTIVE_DATE`
- `BODY_TEXT`
- `UNKNOWN`

Examples:

- `제1장 총칙` -> `CHAPTER_HEADING`
- `제1절 통칙` -> `SECTION_HEADING`
- `제1조(목적)` -> `ARTICLE_HEADING`
- `①` -> `CLAUSE_MARKER`
- `1.` -> `ITEM_MARKER`
- `가.` -> `SUB_ITEM_MARKER`

Interface:

```python
class LineClassifier(Protocol):
    def classify(self, lines: list[SourceLine]) -> list[ClassifiedLine]:
        ...
```

Classification should include confidence and matched pattern name. That makes
parser failures debuggable.

### 5. Hierarchy Parsing

The hierarchy parser consumes classified lines and builds the canonical legal
tree.

Recommended approach:

- Use a deterministic state machine with an explicit parse context.
- Keep the current open `Chapter`, `Section`, `Article`, `Clause`, and `Item`.
- When a higher-level marker appears, close lower-level nodes first.
- Attach body text to the lowest valid open node.
- If an article contains body text without a numbered clause, create an
  unnumbered `Clause`.
- Preserve direct articles under chapters when no section exists.
- Preserve parser diagnostics instead of guessing when structure is ambiguous.

Interface:

```python
class HierarchyParser(Protocol):
    def parse(self, document: CleanDocument) -> ParseResult:
        ...
```

`ParseResult` should contain:

- `RegulationDocument`
- diagnostics
- parse statistics
- unrecovered lines, if any

### 6. Metadata Enrichment

After the tree is built, enrichment stages attach derived metadata.

Responsibilities:

- Regulation title detection.
- Effective date detection.
- Amendment history detection.
- Provision status detection: active, repealed, deleted, unknown.
- Article-level metadata normalization.
- Reference detection.
- Incompleteness flag detection.
- Appendix and table placeholder detection.

These should be separate stages so hierarchy parsing stays focused.

Interface:

```python
class EnrichmentPass(Protocol):
    def apply(self, document: RegulationDocument) -> RegulationDocument:
        ...
```

Enrichment passes must never delete source text.

### 7. Validation and Diagnostics

Validation checks the parsed model before export.

Responsibilities:

- Verify hierarchy order.
- Verify required article metadata.
- Verify every node has an ID and path.
- Verify source spans are present where extraction provided them.
- Verify references are either resolved or explicitly unresolved/missing.
- Verify unknown lines are reported.
- Verify serialization can round-trip without changing structure.

Validation should not silently mutate the document. It should return structured
diagnostics.

## Proposed Modules

```text
unireg/
  extractors/
    base.py
    pdf.py
    hwp.py
  cleaning/
    cleaner.py
    whitespace.py
    headers.py
  parser/
    patterns.py
    classifier.py
    context.py
    ids.py
    document_parser.py
    chapter_parser.py
    section_parser.py
    article_parser.py
    clause_parser.py
    item_parser.py
    sub_item_parser.py
    appendix_parser.py
    table_parser.py
    diagnostics.py
    result.py
  enrichment/
    amendments.py
    statuses.py
    references.py
    incompleteness.py
  validation/
    hierarchy.py
    provenance.py
    references.py
  models/
    ...
  exporters/
    markdown.py
    json.py
```

Keep `models` independent. Parser code can import models, but models must not
import parser code.

## Module Responsibilities

### `extractors`

Owns source-file-specific extraction.

- `base.py`: extractor protocol and extracted document records.
- `pdf.py`: PDF extraction implementation.
- `hwp.py`: future HWP extraction adapter.

### `cleaning`

Owns text normalization and source-map preservation.

- `cleaner.py`: orchestrates cleaning rules.
- `whitespace.py`: normalizes spaces and line endings.
- `headers.py`: detects repeated headers and footers.

### `parser.patterns`

Owns regex patterns and marker normalization.

Pattern categories:

- chapter headings
- section headings
- article headings
- clause markers
- item markers
- sub-item markers
- amendment notes
- effective dates
- appendix headings
- table markers

The parser should centralize patterns here so institution-specific profiles can
override them later.

### `parser.classifier`

Classifies clean lines into structural tokens.

It should not create model nodes. It should return line classifications with:

- token kind
- parsed number, if available
- parsed title, if available
- confidence
- pattern name
- source span

### `parser.document_parser`

Coordinates the parsing process.

Responsibilities:

- Receive classified lines.
- Initialize parse context.
- Dispatch lines to level-specific parsers.
- Close open nodes.
- Return `ParseResult`.

### Level-Specific Parsers

Each level-specific parser should only know how to create or update its level.

- `chapter_parser.py`: chapter creation and chapter transitions.
- `section_parser.py`: optional section creation and transitions.
- `article_parser.py`: article creation, title parsing, article body handling.
- `clause_parser.py`: numbered and unnumbered clauses.
- `item_parser.py`: numbered item parsing.
- `sub_item_parser.py`: Korean-letter sub-item parsing.
- `appendix_parser.py`: appendix structure.
- `table_parser.py`: table placeholder records.

### `parser.context`

Holds current parser state.

Expected state:

- current regulation
- current chapter
- current section
- current article
- current clause
- current item
- diagnostics
- ID builder
- parser configuration

### `parser.ids`

Builds deterministic IDs and paths.

Rules:

- IDs must be stable across runs.
- Legal numbers remain strings.
- IDs should not depend only on list index.
- Inserted articles such as `제1조의2` must be addressable.

### `enrichment`

Runs after hierarchy parsing.

- `amendments.py`: detects enactment, amendment, insertion, repeal history.
- `statuses.py`: marks repealed/deleted/unknown provisions.
- `references.py`: detects references to other articles, rules, guidelines, or
  administrative decisions.
- `incompleteness.py`: creates flags for missing or unresolved rules.

### `validation`

Checks model invariants and produces diagnostics.

Validation should be callable in tests and from the CLI/library API.

## Interfaces

The public parser interface should be small.

```python
class RegulationParser(Protocol):
    def parse_file(self, source_file: Path) -> ParseResult:
        ...

    def parse_text(
        self,
        text: str,
        *,
        source_file: str,
    ) -> ParseResult:
        ...
```

`parse_file` uses extractors. `parse_text` is for tests, fixtures, and already
extracted text.

Core result:

```python
@dataclass(slots=True, kw_only=True)
class ParseResult:
    document: RegulationDocument | None
    diagnostics: list[ParseDiagnostic]
    stats: ParseStats


@dataclass(slots=True, kw_only=True)
class ParseDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    source_span: SourceSpan | None = None
    line_text: str | None = None


@dataclass(slots=True, kw_only=True)
class ParseStats:
    line_count: int
    parsed_line_count: int
    unknown_line_count: int
    article_count: int
    diagnostic_count: int
```

Diagnostics are part of the parser contract. A parse can succeed with warnings
when the legal tree is usable but some lines are uncertain.

## Error Handling

Use structured diagnostics for recoverable problems and exceptions for
programming or environment failures.

Recoverable diagnostics:

- unknown line classification
- article found before chapter
- clause found before article
- item found before clause
- skipped repeated header/footer
- suspicious numbering jump
- missing source span
- unresolved reference
- table extraction incomplete

Fatal errors:

- unreadable input file
- unsupported file type with no extractor
- extractor crash
- impossible model invariant after parsing
- serializer failure during required validation

Recommended severity levels:

- `INFO`: expected recovery or normalization note.
- `WARNING`: parse completed, but some structure is uncertain.
- `ERROR`: parsed document is incomplete or structurally invalid.
- `FATAL`: no usable document can be produced.

The parser should prefer partial structured output with diagnostics over a flat
plain-text fallback.

## Test Strategy

Parser accuracy matters more than speed. Tests should be fixture-driven and
incremental.

### Unit Tests

Test each parser module independently:

- marker regexes in `patterns.py`
- line classification
- chapter transitions
- section transitions
- article heading and title parsing
- unnumbered article body handling
- clause parsing
- item parsing
- sub-item parsing
- appendix/table placeholders
- ID and path generation
- diagnostic generation

### Golden Fixture Tests

Golden tests should parse representative regulation snippets and compare the
result to expected JSON snapshots.

Fixture categories:

- basic chapter/article/clause hierarchy
- chapter with no section
- chapter with sections
- article with no numbered clause
- article with clauses, items, and sub-items
- inserted article such as `제1조의2`
- repealed/deleted article
- amendment history lines
- effective date line
- unresolved reference such as `세부사항은 따로 정한다`
- appendix marker
- table placeholder
- noisy PDF extraction with page headers and footers

### Property and Invariant Tests

Use invariant tests even before broad real-world coverage:

- serialization round-trip preserves IDs and text
- every child path extends parent path
- every article has article number and regulation title
- every citeable node has source metadata when input provided it
- no parsed node is orphaned
- unknown lines appear in diagnostics

### Regression Tests

Every real parsing bug should create a minimal fixture before fixing behavior.

Regression fixtures should be small and named after the parsing issue, not the
institution, unless institution-specific behavior matters.

### Accuracy Evaluation

Eventually maintain an evaluation corpus with manually reviewed expected output.

Metrics:

- article boundary accuracy
- clause boundary accuracy
- item/sub-item boundary accuracy
- source page accuracy
- amendment detection accuracy
- unresolved-reference detection accuracy
- unknown-line rate

## Extension Points

### File Extractors

New extractors should implement the `TextExtractor` interface.

Expected future extractors:

- HWP
- DOCX
- HTML
- plain text

### Institution Profiles

Institution-specific formatting should be configuration, not hardcoded parser
branches.

Profile settings may include:

- title patterns
- header/footer patterns
- numbering variants
- amendment-note patterns
- appendix/table conventions
- source collection metadata

### Pattern Registry

The classifier should use a pattern registry so new marker styles can be added
without rewriting the parser state machine.

### Enrichment Passes

Metadata and reference detection should be pluggable passes.

Examples:

- stricter amendment parser
- institution-specific reference resolver
- table structure extractor
- appendix parser
- cross-regulation resolver

### Exporters

Markdown, JSON, graph, vector, and citation outputs should remain downstream
projections from `RegulationDocument`.

The parser should not depend on any exporter.

## Implementation Order

Recommended parser build order:

1. Define parser-facing extraction and clean-document records.
2. Implement marker patterns and line classifier tests.
3. Implement ID/path generation.
4. Implement document parser context.
5. Implement chapter and article parsing.
6. Add clauses.
7. Add items and sub-items.
8. Add sections.
9. Add source span propagation.
10. Add validation and diagnostics.
11. Add amendment/status enrichment.
12. Add reference and incompleteness enrichment.
13. Add appendices and table placeholders.

This order creates a usable legal tree early while keeping harder metadata and
edge cases as explicit later passes.
