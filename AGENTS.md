# AGENTS

## Goal

Develop a regulation parser for university regulations.

The parser should understand legal document hierarchy instead of treating documents as plain text.

## General Rules

- Python 3.12
- Type hints required
- Dataclasses preferred
- Ruff
- Black
- pytest

## Parsing Rules

Hierarchy:

Regulation

↓

Chapter

↓

Section (optional)

↓

Article

↓

Clause

↓

Item

↓

Sub-item

Preserve hierarchy.

Never flatten legal structures.

## Metadata

Each article should preserve:

- Regulation name
- Chapter
- Article number
- Article title
- Amendment history
- Source page
- Source file

## Output

- Markdown
- JSON
- Future:
    - Knowledge Graph
    - Vector DB

## Testing

Every parser module should include unit tests.

Parser accuracy is more important than speed.

## Grounding Rules

Never invent missing regulations.

If a rule says "세부사항은 따로 정한다" and the referenced document is not available, preserve this as an unresolved reference.

The QA system must distinguish:

- Answered
- Partially answered
- Not answerable from current corpus
- Requires missing regulation
