# Data Model

This document defines the target Python data model for parsed regulations.

The parser should produce a legal hierarchy first. Graph records, vector
documents, citations, Markdown, and JSON are projections from that hierarchy,
not separate sources of truth.

## Current Weaknesses

The previous model was useful as a sketch, but it was not sufficient for a
parser that must support grounded QA.

Missing pieces:

- `Section`, even though sections are part of the required hierarchy.
- `SubItem`, even though sub-items are part of the required hierarchy.
- Stable identifiers for regulations and legal nodes.
- Source provenance: source file, source page, character offsets, extraction
  method, and raw text hash.
- Article-level metadata required by `AGENTS.md`.
- Amendment history and provision status.
- Appendix and table representation.
- Explicit serialization contract and schema versioning.
- Graph projection types.
- Vector DB chunk projection types.
- Citation projection types.

## Design Principles

- Preserve hierarchy. Never flatten legal structures into plain chunks as the
  canonical model.
- Use Python `dataclasses` for the core model.
- Use explicit enums instead of ad hoc strings for statuses and node types.
- Serialize to plain JSON-compatible dictionaries.
- Include a schema version at export boundaries.
- Store source spans on every citeable node.
- Keep embeddings, graph database IDs, and LLM answers out of the core parsed
  model.
- Make future systems derive from stable node IDs and source spans.

## Proposed Module Layout

Future implementation should keep the model separate from parser logic.

```text
unireg/
  models/
    __init__.py
    enums.py
    source.py
    amendments.py
    references.py
    hierarchy.py
    serialization.py
    graph.py
    vector.py
    citation.py
```

No parser module should be required to import graph, vector, or RAG code.

## Identifiers

Every addressable legal node needs a stable ID.

Recommended IDs:

- `regulation_id`: stable regulation identifier.
- `node_id`: stable legal node identifier.
- `path`: ordered hierarchy path from regulation to node.

Examples:

```text
regulation_id = "university-a:graduate-school-regulation:2025-03-01"
node_id = "university-a:graduate-school-regulation:2025-03-01/article:1/clause:1"
path = ["chapter:1", "article:1", "clause:1"]
```

IDs should be deterministic and should not depend on list indexes alone. Korean
article numbers such as `제1조의2` must be preserved as strings.

## Enums

The model should use enums for values that affect behavior.

```python
from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    REGULATION = "regulation"
    CHAPTER = "chapter"
    SECTION = "section"
    ARTICLE = "article"
    CLAUSE = "clause"
    ITEM = "item"
    SUB_ITEM = "sub_item"
    APPENDIX = "appendix"
    TABLE = "table"


class ProvisionStatus(StrEnum):
    ACTIVE = "active"
    REPEALED = "repealed"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class AmendmentEventType(StrEnum):
    ENACTED = "enacted"
    AMENDED = "amended"
    INSERTED = "inserted"
    REPEALED = "repealed"
    EFFECTIVE_DATE_CHANGED = "effective_date_changed"


class ReferenceType(StrEnum):
    EXPLICIT_REFERENCE = "explicit_reference"
    IMPLICIT_REFERENCE = "implicit_reference"
    UNKNOWN_EXTERNAL_RULE = "unknown_external_rule"
    MISSING_INTERNAL_RULE = "missing_internal_rule"
    ADMINISTRATIVE_DISCRETION = "administrative_discretion"


class ReferenceStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    MISSING = "missing"


class IncompletenessType(StrEnum):
    REQUIRES_MISSING_REGULATION = "requires_missing_regulation"
    NOT_ANSWERABLE_FROM_CORPUS = "not_answerable_from_corpus"
    PARTIAL_EVIDENCE_ONLY = "partial_evidence_only"
    ADMINISTRATIVE_DISCRETION = "administrative_discretion"
```

## Source Provenance

Every citeable node should carry source provenance.

```python
from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class SourceSpan:
    source_file: str
    page_start: int | None = None
    page_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    extraction_method: str | None = None
    text_hash: str | None = None
```

Notes:

- `page_start` and `page_end` support PDF citations.
- Character offsets support source-level validation and citation checks.
- `text_hash` allows later verification that citations still match the
  extracted source.
- Raw source text may be stored on nodes as `raw_text`, but large binary files
  should not be embedded in the model.

## Common Node Metadata

Most legal nodes share the same metadata.

```python
from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class LegalNode:
    id: str
    path: list[str]
    node_type: NodeType
    title: str | None = None
    text: str = ""
    source_span: SourceSpan | None = None
    status: ProvisionStatus = ProvisionStatus.ACTIVE
    raw_text: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
```

The concrete hierarchy classes may either inherit from `LegalNode` or compose
the same fields directly. The key requirement is that every legal node has:

- stable `id`
- `node_type`
- hierarchy `path`
- optional `source_span`
- optional `raw_text`
- provision `status`

## Core Hierarchy

The canonical model should preserve the document tree.

```python
from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True, kw_only=True)
class Regulation:
    id: str
    title: str
    node_type: NodeType = field(default=NodeType.REGULATION, init=False)
    path: list[str] = field(default_factory=list)
    institution: str | None = None
    effective_date: date | None = None
    amendment_date: date | None = None
    source_span: SourceSpan | None = None
    amendment_history: list[AmendmentEvent] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    appendices: list[Appendix] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Chapter(LegalNode):
    node_type: NodeType = field(default=NodeType.CHAPTER, init=False)
    number: str
    children: list[Section | Article] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Section(LegalNode):
    node_type: NodeType = field(default=NodeType.SECTION, init=False)
    number: str
    articles: list[Article] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Article(LegalNode):
    node_type: NodeType = field(default=NodeType.ARTICLE, init=False)
    article_number: str
    regulation_title: str
    chapter_title: str | None = None
    section_title: str | None = None
    amendment_history: list[AmendmentEvent] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    incompleteness_flags: list[IncompletenessFlag] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Clause(LegalNode):
    node_type: NodeType = field(default=NodeType.CLAUSE, init=False)
    clause_number: str | None = None
    items: list[Item] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Item(LegalNode):
    node_type: NodeType = field(default=NodeType.ITEM, init=False)
    item_number: str
    sub_items: list[SubItem] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class SubItem(LegalNode):
    node_type: NodeType = field(default=NodeType.SUB_ITEM, init=False)
    sub_item_number: str
    references: list[Reference] = field(default_factory=list)
```

Important modeling choices:

- `Chapter.children` preserves order when a chapter contains sections and
  direct articles.
- For `Article`, the inherited `title` field is the article title.
- `Clause.clause_number` is optional because some articles contain unnumbered
  body text. That text should still be represented as a clause-like node rather
  than flattened into the article.
- All legal numbers are strings. Do not coerce Korean legal numbers into
  integers.

## Amendments

Amendment information should be attached to the article or node it affects.

```python
@dataclass(slots=True, kw_only=True)
class AmendmentEvent:
    event_type: AmendmentEventType
    date: date | None = None
    raw_text: str = ""
    source_span: SourceSpan | None = None
    note: str | None = None
```

Examples of amendment events:

- enacted
- amended
- inserted
- repealed
- effective date changed

## References and Incompleteness

References must preserve unresolved and missing rules. Do not invent targets.

```python
@dataclass(slots=True, kw_only=True)
class Reference:
    id: str
    source_node_id: str
    reference_type: ReferenceType
    status: ReferenceStatus
    raw_text: str
    target_name: str | None = None
    target_type: str | None = None
    target_node_id: str | None = None
    required_document_name: str | None = None
    confidence: float | None = None
    source_span: SourceSpan | None = None


@dataclass(slots=True, kw_only=True)
class IncompletenessFlag:
    id: str
    node_id: str
    flag_type: IncompletenessType
    raw_text: str
    missing_source: str | None = None
    source_span: SourceSpan | None = None
    note: str | None = None
```

These records support later answer states:

- answered
- partially answered
- not answerable from current corpus
- requires missing regulation

The answer state itself belongs to the QA layer, but the parsed model must carry
the evidence needed to derive it.

## Appendices and Tables

Appendices and tables should be represented explicitly because they often carry
binding legal content.

```python
@dataclass(slots=True, kw_only=True)
class Appendix(LegalNode):
    node_type: NodeType = field(default=NodeType.APPENDIX, init=False)
    number: str | None = None
    tables: list[Table] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Table(LegalNode):
    node_type: NodeType = field(default=NodeType.TABLE, init=False)
    caption: str | None = None
    rows: list[list[str]] = field(default_factory=list)
```

If table extraction is incomplete, preserve a table placeholder with source
metadata and raw text instead of dropping it.

## Serialization

All model objects should serialize to JSON-compatible dictionaries.

Recommended contract:

```python
SCHEMA_VERSION = "unireg.regulation.v1"


@dataclass(slots=True, kw_only=True)
class RegulationDocument:
    schema_version: str
    regulation: Regulation

    def to_dict(self) -> dict[str, object]:
        ...

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RegulationDocument":
        ...
```

Serialization rules:

- Include `schema_version` at the document root.
- Serialize dates as ISO 8601 strings.
- Serialize enums using their string values.
- Preserve list order.
- Preserve IDs exactly.
- Omit `None` only if the JSON schema explicitly allows omission.
- Unknown future fields should be rejected in strict mode and preserved in
  compatibility mode only if explicitly supported.

The JSON export should be treated as a versioned public contract, not merely a
debug dump of Python objects.

## Graph Support

The core model should not depend on a graph database. Instead, expose graph
projection records.

```python
@dataclass(slots=True, kw_only=True)
class GraphNode:
    id: str
    node_type: NodeType
    label: str
    properties: dict[str, str]


@dataclass(slots=True, kw_only=True)
class GraphEdge:
    source_id: str
    target_id: str | None
    edge_type: str
    properties: dict[str, str]
```

Expected graph edges:

- `CONTAINS`: regulation to chapter, chapter to section/article, article to
  clause, clause to item, item to sub-item.
- `REFERS_TO`: resolved legal reference.
- `MISSING_REFERENCE`: unresolved or missing referenced rule.
- `HAS_APPENDIX`: regulation or article to appendix.
- `HAS_TABLE`: legal node to table.
- `AMENDED_BY`: node to amendment event, if amendment events become graph nodes.

Missing references should still produce graph edges with `target_id=None` and
the missing target name in edge properties.

## Vector DB Support

Embeddings should not be stored in the core regulation model. Vector documents
should be derived from citeable legal nodes.

```python
@dataclass(slots=True, kw_only=True)
class VectorDocument:
    chunk_id: str
    node_id: str
    regulation_id: str
    text: str
    metadata: dict[str, str]
    source_span: SourceSpan | None = None
```

Recommended chunk levels:

- article
- clause
- item

Required vector metadata:

- regulation ID and title
- institution
- chapter number and title
- section number and title, if present
- article number and title
- node type
- provision status
- source file
- source page range
- incompleteness flags

Vector chunks must preserve enough metadata to reconstruct citations and
answerability decisions without reparsing the source document.

## Citation Support

Citations should be derived from legal nodes and source spans.

```python
@dataclass(slots=True, kw_only=True)
class Citation:
    node_id: str
    node_type: NodeType
    regulation_title: str
    label: str
    source_label: str
    source_span: SourceSpan | None
    quote: str | None = None
```

Citation labels and source labels should be deterministic.

Examples:

```text
Graduate School Regulation, Article 1
Graduate School Regulation, Article 1, Clause 1
Graduate School Regulation, Article 1, Clause 1, Item 2
source.pdf p.1
source.pdf pp.1-2
```

Citation generation must not depend on LLM output. It should use the parsed
hierarchy and source metadata.

## Validation Rules

The model layer should support validation independent of parser implementation.

Minimum validation checks:

- Regulation has a non-empty ID and title.
- Every legal node has a stable ID and node type.
- Every child path extends the parent path.
- Every article has regulation and article metadata.
- Every citeable node has source metadata when available from extraction.
- References point to existing node IDs or have unresolved/missing status.
- Repealed nodes preserve source text or amendment text when available.
- Serialization round-trips without changing IDs, hierarchy order, or text.

## Implementation Guidance

Use dataclasses, type hints, and small modules. Keep the parser separate from
the model.

Recommended implementation details:

- `@dataclass(slots=True, kw_only=True)` for model classes.
- `field(default_factory=list)` for mutable collections.
- `StrEnum` for status/type fields.
- Dedicated serializer/deserializer instead of relying only on `asdict`.
- Snapshot tests for JSON exports.
- Unit tests for ID stability, source span preservation, reference statuses,
  graph projection, vector projection, and citation generation.
