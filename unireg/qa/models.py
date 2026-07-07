"""Dataclasses for grounded QA traces."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import StrEnum

from unireg.benchmark.models import GoldCitation


class CompletenessStatus(StrEnum):
    """Answer completeness labels used by grounded QA."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING_REGULATION = "missing_regulation"
    UNKNOWN = "unknown"


class LLMProvider(StrEnum):
    """LLM adapter providers supported by the interface."""

    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    LOCAL = "local"


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceItem:
    """One retrieved legal node included in the LLM evidence package."""

    evidence_id: str
    rank: int
    score: float
    confidence: float
    node_id: str
    node_type: str
    text: str
    citation: GoldCitation
    citation_label: str
    source_label: str
    source_file: str
    source_pages: list[int] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    incompleteness_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "rank": self.rank,
            "score": self.score,
            "confidence": self.confidence,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "text": self.text,
            "citation": self.citation.to_dict(),
            "citation_label": self.citation_label,
            "source_label": self.source_label,
            "source_file": self.source_file,
            "source_pages": self.source_pages,
            "metadata": self.metadata,
            "incompleteness_flags": self.incompleteness_flags,
        }

    def to_llm_dict(self) -> dict[str, object]:
        """Return only fields the LLM is allowed to consume."""

        return {
            "evidence_id": self.evidence_id,
            "rank": self.rank,
            "confidence": self.confidence,
            "text": self.text,
            "citation": self.citation.to_dict(),
            "citation_label": self.citation_label,
            "source_label": self.source_label,
            "source_pages": self.source_pages,
            "metadata": self.metadata,
            "incompleteness_flags": self.incompleteness_flags,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidencePackage:
    """Traceable input package passed to an LLM adapter."""

    package_id: str
    question: str
    retriever: str
    retrieval_scope: str
    top_k: int
    evidence: list[EvidenceItem]
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "question": self.question,
            "retriever": self.retriever,
            "retrieval_scope": self.retrieval_scope,
            "top_k": self.top_k,
            "evidence": [item.to_dict() for item in self.evidence],
            "metadata": self.metadata,
        }

    def to_llm_dict(self) -> dict[str, object]:
        """Return the exact evidence payload consumed by the LLM adapter."""

        return {
            "package_id": self.package_id,
            "question": self.question,
            "retriever": self.retriever,
            "retrieval_scope": self.retrieval_scope,
            "top_k": self.top_k,
            "evidence": [item.to_llm_dict() for item in self.evidence],
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LLMRequest:
    """Exact prompt/input sent to an LLM adapter."""

    request_id: str
    provider: LLMProvider
    model: str
    system_prompt: str
    user_prompt: str
    evidence_package: EvidencePackage

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "provider": self.provider.value,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_prompt},
            ],
            "evidence_package": self.evidence_package.to_dict(),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class LLMResponse:
    """Structured response returned by an LLM adapter."""

    answer: str
    citations: list[GoldCitation]
    completeness_status: CompletenessStatus
    confidence: float
    reasoning_metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "completeness_status": self.completeness_status.value,
            "confidence": self.confidence,
            "reasoning_metadata": self.reasoning_metadata,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class GroundedAnswer:
    """Final grounded answer plus full trace metadata."""

    answer_id: str
    question: str
    answer: str
    citations: list[GoldCitation]
    evidence: list[EvidenceItem]
    completeness_status: CompletenessStatus
    confidence: float
    reasoning_metadata: dict[str, str]
    evidence_package: EvidencePackage
    llm_request: LLMRequest
    llm_response: LLMResponse
    guardrail_events: list[str] = field(default_factory=list)
    evaluation: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "answer_id": self.answer_id,
            "question": self.question,
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "evidence": [item.to_dict() for item in self.evidence],
            "completeness_status": self.completeness_status.value,
            "confidence": self.confidence,
            "reasoning_metadata": self.reasoning_metadata,
            "evidence_package": self.evidence_package.to_dict(),
            "llm_request": self.llm_request.to_dict(),
            "llm_response": self.llm_response.to_dict(),
            "guardrail_events": self.guardrail_events,
            "evaluation": self.evaluation,
            "trace": {
                "question": self.question,
                "retrieved_evidence": [
                    item.to_dict() for item in self.evidence_package.evidence
                ],
                "llm_input": self.llm_request.to_dict(),
                "grounded_answer": {
                    "answer": self.answer,
                    "citations": [citation.to_dict() for citation in self.citations],
                    "completeness_status": self.completeness_status.value,
                    "confidence": self.confidence,
                },
                "evaluation": self.evaluation,
            },
        }

    def with_evaluation(self, evaluation: dict[str, object]) -> GroundedAnswer:
        return replace(self, evaluation=evaluation)


def stable_id(prefix: str, payload: object) -> str:
    """Return a deterministic id for trace artifacts."""

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"
