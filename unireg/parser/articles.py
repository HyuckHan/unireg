"""Article heading parser."""

from __future__ import annotations

from unireg.models import Article, CleanLine, merge_source_spans
from unireg.parser.ids import article_id
from unireg.parser.patterns import ArticleHeading, parse_article_heading


class ArticleParser:
    """Create article nodes from article heading lines."""

    def match(self, line: CleanLine) -> ArticleHeading | None:
        return parse_article_heading(line.text)

    def create_article(
        self,
        *,
        parent_id: str,
        parent_path: list[str],
        regulation_title: str | None = None,
        chapter_title: str | None = None,
        section_title: str | None = None,
        line: CleanLine,
        heading: ArticleHeading,
    ) -> Article:
        article = Article(
            id=article_id(parent_id, heading.id_fragment),
            article_number=heading.article_number,
            title=heading.title,
            path=[*parent_path, f"article:{heading.id_fragment}"],
            source_span=line.source_span,
            regulation_title=regulation_title,
            chapter_title=chapter_title,
            section_title=section_title,
        )
        if heading.body_text is not None:
            article.body_lines.append(heading.body_text)
            article.source_span = merge_source_spans(
                article.source_span,
                line.source_span,
            )
        return article
