"""Evidence package construction for grounded QA."""

from __future__ import annotations

from unireg.qa.models import EvidenceItem, EvidencePackage, stable_id
from unireg.retrieval.bm25 import BM25SearchHit


def build_evidence_package(
    *,
    question: str,
    hits: list[BM25SearchHit],
    retriever: str,
    retrieval_scope: str,
    top_k: int,
    metadata: dict[str, str] | None = None,
) -> EvidencePackage:
    """Build a traceable evidence package from ranked retrieval hits."""

    max_score = max((hit.score for hit in hits), default=0.0)
    evidence = [_evidence_item(hit, max_score=max_score) for hit in hits]
    package_payload = {
        "question": question,
        "retriever": retriever,
        "retrieval_scope": retrieval_scope,
        "top_k": top_k,
        "evidence_ids": [item.evidence_id for item in evidence],
    }
    return EvidencePackage(
        package_id=stable_id("evidence", package_payload),
        question=question,
        retriever=retriever,
        retrieval_scope=retrieval_scope,
        top_k=top_k,
        evidence=evidence,
        metadata=metadata or {},
    )


def _evidence_item(hit: BM25SearchHit, *, max_score: float) -> EvidenceItem:
    document = hit.document
    confidence = 0.0 if max_score <= 0 else hit.score / max_score
    evidence_payload = {
        "rank": hit.rank,
        "node_id": document.node_id,
        "score": f"{hit.score:.8f}",
    }
    return EvidenceItem(
        evidence_id=stable_id("evidence_item", evidence_payload),
        rank=hit.rank,
        score=hit.score,
        confidence=confidence,
        node_id=document.node_id,
        node_type=document.node_type.value,
        text=document.text,
        citation=document.citation,
        citation_label=document.citation_label,
        source_label=document.source_label,
        source_file=document.source_file,
        source_pages=document.source_pages,
        metadata=document.metadata,
        incompleteness_flags=_incompleteness_flags(document.metadata),
    )


def _incompleteness_flags(metadata: dict[str, str]) -> list[str]:
    flags: list[str] = []
    for key in [
        "incompleteness_types",
        "missing_sources",
        "required_documents",
        "reference_statuses",
    ]:
        value = metadata.get(key)
        if value is None:
            continue
        for item in value.split("|"):
            normalized = item.strip()
            if normalized and normalized not in flags:
                flags.append(normalized)
    return flags
