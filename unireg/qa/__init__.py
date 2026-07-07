"""Grounded QA framework for UniReg."""

from unireg.qa.adapters import FutureLLMAdapter, LLMAdapter, MockLLMAdapter
from unireg.qa.evaluation import (
    QAEvaluationMetrics,
    QAEvaluationResult,
    evaluate_qa,
    write_qa_reports,
)
from unireg.qa.evidence import build_evidence_package
from unireg.qa.models import (
    CompletenessStatus,
    EvidenceItem,
    EvidencePackage,
    GroundedAnswer,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from unireg.qa.pipeline import GroundedQAPipeline
from unireg.qa.retrievers import (
    BM25EvidenceRetriever,
    BM25EvidenceRetrieverConfig,
    EvidenceRetriever,
)

__all__ = [
    "BM25EvidenceRetriever",
    "BM25EvidenceRetrieverConfig",
    "CompletenessStatus",
    "EvidenceItem",
    "EvidencePackage",
    "EvidenceRetriever",
    "FutureLLMAdapter",
    "GroundedAnswer",
    "GroundedQAPipeline",
    "LLMAdapter",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "MockLLMAdapter",
    "QAEvaluationMetrics",
    "QAEvaluationResult",
    "build_evidence_package",
    "evaluate_qa",
    "write_qa_reports",
]
