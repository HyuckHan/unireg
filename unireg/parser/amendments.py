"""Amendment history and provision status enrichment."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

from unireg.models import (
    AmendmentEvent,
    AmendmentEventType,
    Article,
    ProvisionStatus,
    Regulation,
    SourceSpan,
)

_DATE_RE = re.compile(
    r"(?P<year>\d{4})\s*\.\s*(?P<month>\d{1,2})\s*\.\s*(?P<day>\d{1,2})\s*\.?"
)
_ANGLE_EVENT_RE = re.compile(r"<[^>]*(개정|신설|삭제|폐지)[^>]*>")
_STATUS_DATE_EVENT_RE = re.compile(
    r"(삭제|폐지)\s*<[^>]*\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\.?[^>]*>"
)
_BRACKET_EVENT_RE = re.compile(
    r"\[[^\]]*(본조\s*신설|본조\s*삭제|본조\s*폐지|제목변경|항변경|이동)[^\]]*\]"
)
_EFFECTIVE_DATE_RE = re.compile(r"\[시행\s*(?P<date>[^\]]+)\]")
_REGULATION_AMENDMENT_RE = re.compile(
    r"\[(?P<date>\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\.?)\s*,?\s*"
    r"(?P<kind>일부개정|전부개정|개정)\]"
)


class AmendmentStatusEnricher:
    """Attach amendment history and provision status to parsed nodes."""

    def enrich(self, regulation: Regulation) -> Regulation:
        self._enrich_regulation(regulation)
        for article in regulation.all_articles():
            self._enrich_article(article)
        return regulation

    def _enrich_regulation(self, regulation: Regulation) -> None:
        effective_match = _EFFECTIVE_DATE_RE.search(regulation.title)
        if effective_match is not None:
            dates = _extract_dates(effective_match.group("date"))
            if dates:
                regulation.effective_date = dates[0]

        amendment_match = _REGULATION_AMENDMENT_RE.search(regulation.title)
        if amendment_match is not None:
            dates = _extract_dates(amendment_match.group("date"))
            if dates:
                regulation.amendment_date = dates[0]
                regulation.amendment_history.append(
                    AmendmentEvent(
                        event_type=AmendmentEventType.AMENDED,
                        date=dates[0],
                        raw_text=amendment_match.group(0),
                        source_span=regulation.source_span,
                    )
                )

    def _enrich_article(self, article: Article) -> None:
        text_parts = [
            part
            for part in [article.title, *article.body_lines]
            if part is not None and part
        ]
        text = " ".join(text_parts)
        article.status = _detect_article_status(article=article, text=text)
        article.amendment_history.extend(
            _extract_amendment_events(text, source_span=article.source_span)
        )


def _detect_article_status(*, article: Article, text: str) -> ProvisionStatus:
    title = (article.title or "").strip()
    normalized_text = re.sub(r"\s+", "", text)
    first_body = article.body_lines[0].strip() if article.body_lines else ""

    if (
        title.startswith("폐지")
        or first_body.startswith("폐지")
        or "본조폐지" in normalized_text
    ):
        return ProvisionStatus.REPEALED
    if (
        title.startswith("삭제")
        or first_body.startswith("삭제")
        or "본조삭제" in normalized_text
    ):
        return ProvisionStatus.DELETED
    return ProvisionStatus.ACTIVE


def _extract_amendment_events(
    text: str,
    *,
    source_span: SourceSpan | None,
) -> list[AmendmentEvent]:
    events: list[AmendmentEvent] = []
    for raw_text in _iter_event_markers(text):
        event_type = _event_type(raw_text)
        dates = _extract_dates(raw_text)
        if dates:
            events.extend(
                AmendmentEvent(
                    event_type=event_type,
                    date=event_date,
                    raw_text=raw_text,
                    source_span=source_span,
                )
                for event_date in dates
            )
        else:
            events.append(
                AmendmentEvent(
                    event_type=event_type,
                    raw_text=raw_text,
                    source_span=source_span,
                )
            )
    return events


def _iter_event_markers(text: str) -> Iterable[str]:
    matches = [
        *(_STATUS_DATE_EVENT_RE.finditer(text)),
        *(_ANGLE_EVENT_RE.finditer(text)),
        *(_BRACKET_EVENT_RE.finditer(text)),
    ]
    emitted_ranges: list[tuple[int, int]] = []
    for match in sorted(matches, key=lambda item: item.start()):
        if any(
            match.start() >= start and match.end() <= end
            for start, end in emitted_ranges
        ):
            continue
        emitted_ranges.append((match.start(), match.end()))
        yield match.group(0)


def _event_type(raw_text: str) -> AmendmentEventType:
    compact = re.sub(r"\s+", "", raw_text)
    if "신설" in compact:
        return AmendmentEventType.INSERTED
    if "삭제" in compact or "폐지" in compact:
        return AmendmentEventType.REPEALED
    return AmendmentEventType.AMENDED


def _extract_dates(text: str) -> list[date]:
    dates: list[date] = []
    for match in _DATE_RE.finditer(text):
        dates.append(
            date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        )
    return dates
