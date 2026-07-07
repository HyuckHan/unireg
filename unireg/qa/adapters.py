"""LLM adapter interfaces for grounded QA."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from unireg.benchmark.models import GoldCitation
from unireg.qa.models import (
    CompletenessStatus,
    EvidenceItem,
    EvidencePackage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    stable_id,
)

SYSTEM_PROMPT = (
    "You answer institutional regulation questions only from the supplied "
    "EvidencePackage. Do not invent regulations. If evidence is insufficient, "
    "return an incomplete answer."
)


class LLMAdapter(ABC):
    """Abstract LLM adapter boundary."""

    provider: LLMProvider
    model: str

    def build_request(self, evidence_package: EvidencePackage) -> LLMRequest:
        """Build the exact request sent to this adapter."""

        user_prompt = json.dumps(
            evidence_package.to_llm_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        payload = {
            "provider": self.provider.value,
            "model": self.model,
            "evidence_package": evidence_package.to_llm_dict(),
        }
        return LLMRequest(
            request_id=stable_id("llm_request", payload),
            provider=self.provider,
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            evidence_package=evidence_package,
        )

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Generate a structured response from an LLM request."""


class MockLLMAdapter(LLMAdapter):
    """Deterministic adapter used for tests and offline development."""

    provider = LLMProvider.MOCK
    model = "mock-grounded-v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        package = request.evidence_package
        if not package.evidence:
            return LLMResponse(
                answer="검색된 근거가 없어 현재 corpus만으로는 답할 수 없습니다.",
                citations=[],
                completeness_status=CompletenessStatus.UNKNOWN,
                confidence=0.0,
                reasoning_metadata={"mock_policy": "no_evidence"},
            )

        top_evidence = package.evidence[0]
        if _has_missing_regulation_signal([top_evidence]):
            return LLMResponse(
                answer=(
                    "제공된 근거는 세부사항을 별도 규정이나 기관 결정에 "
                    "위임하고 있어 현재 corpus만으로는 완전한 답변을 할 수 "
                    f"없습니다. 근거: {_short_quote(top_evidence.text)}"
                ),
                citations=[top_evidence.citation],
                completeness_status=CompletenessStatus.MISSING_REGULATION,
                confidence=top_evidence.confidence,
                reasoning_metadata={
                    "mock_policy": "missing_regulation_signal",
                    "top_evidence_id": top_evidence.evidence_id,
                },
            )

        return LLMResponse(
            answer=(
                "제공된 근거에 따르면 다음 조항이 질문과 관련됩니다: "
                f"{_short_quote(top_evidence.text)}"
            ),
            citations=[top_evidence.citation],
            completeness_status=CompletenessStatus.COMPLETE,
            confidence=top_evidence.confidence,
            reasoning_metadata={
                "mock_policy": "top_evidence_extractive",
                "top_evidence_id": top_evidence.evidence_id,
            },
        )


class FutureLLMAdapter(LLMAdapter):
    """Placeholder for online or local providers implemented after this milestone."""

    def __init__(self, *, provider: LLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError(
            f"{self.provider.value} adapter is intentionally not implemented."
        )


def _has_missing_regulation_signal(evidence: list[EvidenceItem]) -> bool:
    signal_tokens = [
        "requires_missing_regulation",
        "administrative_discretion",
        "missing",
        "unresolved",
    ]
    text_tokens = [
        "세부사항은",
        "세부 사항은",
        "따로 정한다",
        "별도로 정한다",
        "총장이 따로 정한다",
    ]
    for item in evidence:
        if any(token in item.incompleteness_flags for token in signal_tokens):
            return True
        if any(token in item.text for token in text_tokens):
            return True
    return False


def _short_quote(text: str, *, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def citations_from_evidence(evidence: list[EvidenceItem]) -> list[GoldCitation]:
    """Return citations for evidence items, preserving rank order."""

    return [item.citation for item in evidence]
