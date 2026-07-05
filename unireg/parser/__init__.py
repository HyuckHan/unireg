"""Regulation parser."""

from unireg.parser.amendments import AmendmentStatusEnricher
from unireg.parser.appendices import AppendixParser
from unireg.parser.clauses import ClauseParser
from unireg.parser.items import ItemParser
from unireg.parser.metadata import (
    MetadataWarning,
    RegulationMetadata,
    RegulationMetadataNormalizer,
)
from unireg.parser.parser import RegulationParser
from unireg.parser.references import ReferenceIncompletenessEnricher
from unireg.parser.sections import SectionParser
from unireg.parser.tables import TableParser

__all__ = [
    "AmendmentStatusEnricher",
    "AppendixParser",
    "ClauseParser",
    "ItemParser",
    "MetadataWarning",
    "ReferenceIncompletenessEnricher",
    "RegulationMetadata",
    "RegulationMetadataNormalizer",
    "RegulationParser",
    "SectionParser",
    "TableParser",
]
