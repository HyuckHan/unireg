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
