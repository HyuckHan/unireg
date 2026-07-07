"""Grounded QA pipeline."""

from __future__ import annotations

from dataclasses import replace

from unireg.qa.adapters import LLMAdapter, MockLLMAdapter
from unireg.qa.citations import citation_is_supported, dedupe_citations
from unireg.qa.evidence import build_evidence_package
from unireg.qa.models import (
    CompletenessStatus,
    GroundedAnswer,
    LLMResponse,
    stable_id,
)
from unireg.qa.retrievers import EvidenceRetriever


class GroundedQAPipeline:
    """Question -> retriever -> evidence package -> LLM adapter -> answer."""

    def __init__(
        self,
        *,
        retriever: EvidenceRetriever,
        llm_adapter: LLMAdapter | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm_adapter = llm_adapter or MockLLMAdapter()

    def answer(
        self,
        question: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> GroundedAnswer:
        active_metadata = metadata or {}
        retriever_config = self._retriever.trace_config()
        hits = self._retriever.retrieve(question, metadata=active_metadata)
        evidence_package = build_evidence_package(
            question=question,
            hits=hits,
            retriever=str(retriever_config.get("method", "unknown")),
            retrieval_scope=str(retriever_config.get("scope", "unknown")),
            top_k=int(retriever_config.get("top_k", len(hits))),
            metadata={
                **active_metadata,
                "retriever_config": _stringify_config(retriever_config),
            },
        )
        llm_request = self._llm_adapter.build_request(evidence_package)
        llm_response = self._llm_adapter.complete(llm_request)
        guarded_response, guardrail_events = _apply_guardrails(
            response=llm_response,
            evidence_package=evidence_package,
        )
        answer_payload = {
            "question": question,
            "evidence_package_id": evidence_package.package_id,
            "llm_request_id": llm_request.request_id,
            "answer": guarded_response.answer,
            "citations": [
                citation.to_dict() for citation in guarded_response.citations
            ],
            "completeness_status": guarded_response.completeness_status.value,
        }
        return GroundedAnswer(
            answer_id=stable_id("answer", answer_payload),
            question=question,
            answer=guarded_response.answer,
            citations=guarded_response.citations,
            evidence=evidence_package.evidence,
            completeness_status=guarded_response.completeness_status,
            confidence=guarded_response.confidence,
            reasoning_metadata={
                **guarded_response.reasoning_metadata,
                "evidence_package_id": evidence_package.package_id,
                "llm_request_id": llm_request.request_id,
                "retriever": str(retriever_config.get("method", "unknown")),
                "guardrail_event_count": str(len(guardrail_events)),
            },
            evidence_package=evidence_package,
            llm_request=llm_request,
            llm_response=llm_response,
            guardrail_events=guardrail_events,
        )


def _apply_guardrails(
    *,
    response: LLMResponse,
    evidence_package,
) -> tuple[LLMResponse, list[str]]:
    events: list[str] = []
    supported_citations = [
        citation
        for citation in response.citations
        if citation_is_supported(citation, evidence_package.evidence)
    ]
    if len(supported_citations) != len(response.citations):
        events.append("unsupported_citations_removed")

    supported_citations = dedupe_citations(supported_citations)
    if not evidence_package.evidence:
        if response.completeness_status != CompletenessStatus.UNKNOWN:
            events.append("no_evidence_forced_unknown")
        return (
            LLMResponse(
                answer="검색된 근거가 없어 현재 corpus만으로는 답할 수 없습니다.",
                citations=[],
                completeness_status=CompletenessStatus.UNKNOWN,
                confidence=0.0,
                reasoning_metadata={
                    **response.reasoning_metadata,
                    "guardrail": "no_evidence",
                },
            ),
            events,
        )

    if (
        response.completeness_status == CompletenessStatus.COMPLETE
        and not supported_citations
    ):
        events.append("complete_answer_without_supported_citation_downgraded")
        return (
            LLMResponse(
                answer=(
                    "검색된 근거는 있으나, 답변을 뒷받침하는 citation이 없어 "
                    "완전한 답변으로 처리할 수 없습니다."
                ),
                citations=[],
                completeness_status=CompletenessStatus.PARTIAL,
                confidence=0.0,
                reasoning_metadata={
                    **response.reasoning_metadata,
                    "guardrail": "missing_supported_citation",
                },
            ),
            events,
        )

    return (
        replace(response, citations=supported_citations),
        events,
    )


def _stringify_config(config: dict[str, object]) -> str:
    return ";".join(f"{key}={value}" for key, value in sorted(config.items()))
