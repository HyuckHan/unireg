"""UniReg regulation parser."""

from unireg.cleaning import DocumentCleaner
from unireg.loaders import PDFLoader
from unireg.models import (
    AmendmentEvent,
    AmendmentEventType,
    Appendix,
    Article,
    Chapter,
    Clause,
    IncompletenessFlag,
    IncompletenessType,
    Item,
    NodeType,
    ProvisionStatus,
    Reference,
    ReferenceStatus,
    ReferenceType,
    Regulation,
    RegulationDocument,
    Section,
    SourceSpan,
    SubItem,
)
from unireg.parser import RegulationParser

__all__ = [
    "AmendmentEvent",
    "AmendmentEventType",
    "Appendix",
    "Article",
    "Chapter",
    "Clause",
    "DocumentCleaner",
    "IncompletenessFlag",
    "IncompletenessType",
    "Item",
    "NodeType",
    "PDFLoader",
    "ProvisionStatus",
    "Reference",
    "ReferenceStatus",
    "ReferenceType",
    "Regulation",
    "RegulationDocument",
    "RegulationParser",
    "Section",
    "SourceSpan",
    "SubItem",
]
