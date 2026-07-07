# Paper Plan

Working Title

Hierarchical Grounded Question Answering over Institutional Regulations

---

Research Questions

RQ1

Can institutional regulations be parsed into a structured hierarchical representation?

RQ2

Does hierarchical retrieval outperform conventional chunk-based retrieval?

RQ3

Can grounded QA reduce hallucination under incomplete regulation corpora?

RQ4

How robust is the parser across multiple universities?

---

Expected Contributions

1.

Open-source regulation parser

2.

UniRegBench benchmark

3.

Hierarchical retrieval

4.

Grounded QA for incomplete regulations

---

Expected Experiments

Parser

Retrieval

- BM25 baseline over UniRegBench questions
- Article, clause, item, and sub-item retrieval units
- Recall@1, Recall@3, Recall@5, MRR, and nDCG@5
- Future comparison against dense, hybrid, and hierarchical retrieval

QA

- LLM-independent grounded QA pipeline
- Evidence Package trace from retrieval to answer
- MockLLM baseline before online provider experiments
- Citation accuracy, groundedness, completeness classification, hallucination
  rate
- Missing-regulation aware answer status
- Explainability and error analysis over QA traces
- Multi-label failure taxonomy for retrieval, citation, completeness,
  hallucination, metadata, and missing-regulation errors

Cross-university

Missing regulation

Experiment Reproducibility

- JSON configs for each experiment
- Run metadata with git commit, Python version, input paths, output paths, and
  random seed
- Paper-style tables generated from saved run artifacts
- Offline synthetic sample for CI and artifact validation

---

Future Work

Knowledge Graph

Temporal Regulations

Automatic Reference Resolution
