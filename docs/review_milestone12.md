# Milestone 12 Review: Retrieval Evaluation

## What Was Implemented

Milestone 12 added deterministic retrieval evaluation independent from LLMs.

Implemented components:

- `unireg.retrieval` package.
- In-process BM25 baseline with no external dependencies.
- Korean-aware tokenizer using word tokens plus character n-grams.
- Retrieval corpus builder from existing parser projections.
- Article, clause, item, and sub-item retrieval units.
- Benchmark runner over Milestone 11 UniRegBench questions.
- CLI entry points:
  - `scripts/unireg_retrieval.py`
  - `python -m unireg.retrieval`
  - `unireg-retrieval`
- Prediction JSONL output.
- Retrieval JSON report.
- Per-question CSV report.
- Per-hit CSV report.
- Retrieval metrics:
  - Recall@1
  - Recall@3
  - Recall@5
  - MRR
  - nDCG@5
- pytest coverage for BM25 ranking, retrieval-unit generation, hierarchical
  citation matching, runner reports, and benchmark integration.

The current local BM25 result on the five-university `학칙.pdf` benchmark is:

```text
questions=20
documents=2316
Recall@1=0.700
Recall@3=1.000
Recall@5=1.000
MRR=0.842
nDCG@5=0.883
```

## Architectural Decisions

Retrieval was implemented as a separate package.

`unireg.retrieval` is separate from `unireg.parser` and `unireg.benchmark`.
The parser remains the source of structured regulation data, benchmark remains
the evaluation contract, and retrieval owns indexing, ranking, and retrieval-run
artifacts.

The parser was not modified.

Retrieval units are built from `ProjectionBuilder` BM25 documents. This keeps
Milestone 12 downstream of the parser and avoids introducing parser behavior
changes during an evaluation milestone.

The BM25 implementation has no external dependencies.

This keeps experiments deterministic and easy to run in a source checkout. It
also avoids depending on search servers or third-party ranking libraries before
the baseline is understood.

Question-source scope is the default.

The current benchmark questions are university-specific and include a
`source_file`. The default retrieval scope searches only that source file so the
baseline measures whether the correct provision can be found inside the relevant
regulation. A `corpus` scope is also available for cross-university
disambiguation experiments.

Gold citation matching is hierarchical.

If a gold citation specifies only an article, a retrieved clause/item/sub-item
under that article can count as relevant. If a gold citation specifies a clause,
the retrieved unit must be that clause or a descendant. `source_file` remains a
hard constraint when present.

## Trade-Offs

BM25 is simple and reproducible but lexical.

It works well for questions that reuse regulation vocabulary. It is weaker for
semantic paraphrases, abbreviations, and questions whose key terms differ from
the source text.

Article and fine-grained units are evaluated together.

This makes one runner cover all required retrieval unit levels, but it can place
an article parent above the exact clause. That is useful diagnostic information:
Recall@3/5 can be high while Recall@1 exposes ranking granularity problems.

Question-source filtering improves current benchmark stability.

It is appropriate when the user already selected a university/regulation, but it
does not measure full-corpus disambiguation. The `corpus` scope should be used
for cross-university experiments.

nDCG is binary relevance.

The current benchmark does not assign graded relevance. nDCG@5 therefore uses
binary gain and de-duplicates matches to the same gold citation.

## Known Limitations

- Dense retrieval is not implemented.
- Hybrid retrieval is not implemented.
- No reranker is implemented.
- No LLM QA is implemented.
- BM25 tokenization is deterministic but still simple.
- The current benchmark has only 20 questions.
- The current question set is mostly direct lookup.
- The corpus scope has not yet been tuned for same-topic questions across
  universities.
- Reports are generated locally and ignored by git.
- `unireg-eval` PDFs are still local inputs and are not committed.

## Future Work

- Add dense retrieval using local embeddings only after deciding the embedding
  dependency and reproducibility policy.
- Add hybrid retrieval that combines BM25 and vector scores.
- Add hierarchical reranking that prefers exact clause matches over article
  parents when the gold/query implies clause-level evidence.
- Add metadata filters for institution, regulation title, source file, and
  provision status.
- Add corpus-scope benchmark runs for cross-university disambiguation.
- Expand UniRegBench questions to include paraphrases, multi-hop questions, and
  comparison questions.
- Add per-unit reports comparing article-only, clause-only, and mixed-unit
  retrieval.
- Add regression thresholds once the benchmark question set is large enough.

## Recommendations For The Next Milestone

The next milestone should not start full LLM QA yet unless retrieval output
quality is considered sufficient for the target experiment.

Recommended next step:

- Improve retrieval diagnostics and baselines before QA.
- Compare unit configurations:
  - article only
  - clause only
  - article plus clause
  - article plus clause plus item plus sub-item
- Run both `question_source` and `corpus` scopes.
- Add more manually reviewed questions per university.
- Decide whether Milestone 13 should be:
  - retrieval improvement, if ranking quality is still the bottleneck
  - grounded QA, if BM25/hybrid retrieval gives stable top-k evidence

For paper experiments, BM25 from Milestone 12 should be treated as the lexical
baseline against which hierarchical, hybrid, and QA-stage improvements are
compared.
