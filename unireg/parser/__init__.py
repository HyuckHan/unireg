"""Regulation parser."""

from unireg.parser.amendments import AmendmentStatusEnricher
from unireg.parser.clauses import ClauseParser
from unireg.parser.items import ItemParser
from unireg.parser.parser import RegulationParser
from unireg.parser.sections import SectionParser

__all__ = [
    "AmendmentStatusEnricher",
    "ClauseParser",
    "ItemParser",
    "RegulationParser",
    "SectionParser",
]
