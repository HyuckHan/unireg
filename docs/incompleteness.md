# Incompleteness Handling

Institutional regulations are often incomplete.

A public regulation may refer to another internal rule, guideline, manual, or administrative decision that is not included in the corpus.

Examples:

- "세부사항은 따로 정한다."
- "총장이 따로 정한다."
- "별도 규정에 따른다."
- "시행세칙에 따른다."

The system must not hallucinate missing rules.

When referenced rules are unavailable, the system should:

1. Answer only from available evidence.
2. Explicitly state the missing source.
3. Mark the answer as incomplete.
4. Suggest which document is required.
5. Preserve the missing reference as a graph edge.

Reference types:

- EXPLICIT_REFERENCE
- IMPLICIT_REFERENCE
- UNKNOWN_EXTERNAL_RULE
- MISSING_INTERNAL_RULE
- ADMINISTRATIVE_DISCRETION

## Current Parser Support

The parser now preserves deterministic reference metadata for these patterns:

- `세부사항은 따로 정한다`
  - `ReferenceType.IMPLICIT_REFERENCE`
  - `ReferenceStatus.UNRESOLVED`
  - `IncompletenessType.REQUIRES_MISSING_REGULATION`
- `총장이 따로 정한다`
  - `ReferenceType.ADMINISTRATIVE_DISCRETION`
  - `ReferenceStatus.UNRESOLVED`
  - `IncompletenessType.ADMINISTRATIVE_DISCRETION`
- `별도 규정에 따른다`
  - `ReferenceType.MISSING_INTERNAL_RULE`
  - `ReferenceStatus.MISSING`
  - missing source: `별도 규정`
- `시행세칙에 따른다`
  - `ReferenceType.MISSING_INTERNAL_RULE`
  - `ReferenceStatus.MISSING`
  - missing source: `시행세칙`

This is detection, not corpus-level resolution. If the referenced document is
present elsewhere in the corpus, a later resolution phase should connect the
reference to the target node without deleting the original unresolved evidence.
