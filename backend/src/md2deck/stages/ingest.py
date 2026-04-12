from __future__ import annotations

from dataclasses import dataclass
import re

from md2deck.config import AppConfig
from md2deck.models import MarkdownDocument, MarkdownSection, MarkdownTable, PipelineArtifacts


@dataclass(slots=True)
class IngestStage:
    name: str = "ingest"

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        raw_text = config.input_markdown.read_text(encoding="utf-8", errors="replace")
        title = self._extract_title(raw_text, config.input_markdown.stem)
        subtitle = self._extract_subtitle(raw_text)
        cleaned_text = self._clean_markdown(raw_text)
        executive_summary = self._extract_executive_summary(cleaned_text)
        sections = self._parse_sections(cleaned_text)
        tables = [table for section in sections for table in section.tables]
        numeric_facts = self._collect_numeric_facts(cleaned_text)
        artifacts.document = MarkdownDocument(
            path=config.input_markdown,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            title=title,
            subtitle=subtitle,
            executive_summary=executive_summary,
            sections=sections,
            tables=tables,
            numeric_facts=numeric_facts,
        )

    @staticmethod
    def _extract_title(raw_text: str, fallback: str) -> str:
        for line in raw_text.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return fallback

    @staticmethod
    def _extract_subtitle(raw_text: str) -> str:
        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()
        return ""

    def _clean_markdown(self, raw_text: str) -> str:
        cleaned_lines: list[str] = []
        in_toc = False
        in_code_fence = False
        for line in raw_text.replace("\ufeff", "").splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_fence = not in_code_fence
                cleaned_lines.append(line)
                continue
            if in_code_fence:
                cleaned_lines.append(line)
                continue
            if stripped.lower() in {"## table of contents", "## contents"}:
                in_toc = True
                continue
            if in_toc:
                if stripped.startswith("## ") and stripped.lower() not in {"## table of contents", "## contents"}:
                    in_toc = False
                elif stripped.startswith("[") or stripped.startswith("- ["):
                    continue
                elif not stripped:
                    continue
            if stripped.startswith("![") and "data:image" in stripped:
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _extract_executive_summary(self, cleaned_text: str) -> list[str]:
        sections = self._split_by_heading(cleaned_text, "## ")
        summary_block = sections.get("Executive Summary", "")
        if not summary_block:
            return []
        return self._dedupe_points(self._extract_key_points(summary_block, limit=6))[:4]

    def _parse_sections(self, cleaned_text: str) -> list[MarkdownSection]:
        section_map = self._split_by_heading(cleaned_text, "## ")
        parsed_sections: list[MarkdownSection] = []
        for title, content in section_map.items():
            if title in {"Executive Summary", "Table of Contents", "Contents"}:
                continue
            if title == (self._extract_title(cleaned_text, "") or ""):
                continue
            subsection_titles = [name for name in self._split_by_heading(content, "### ").keys()]
            tables = self._extract_tables(content, title)
            body = self._paragraphs_from_text(content)
            bullets = self._dedupe_points(self._extract_key_points(content, limit=15), context=[title] + subsection_titles)[:12]
            numeric_facts = self._dedupe_points(self._collect_numeric_facts(content, limit=20), context=[title])[:15]
            parsed_sections.append(
                MarkdownSection(
                    title=title,
                    level=2,
                    body=self._dedupe_points(body, context=[title])[:8],
                    bullets=bullets,
                    numeric_facts=numeric_facts,
                    subsection_titles=subsection_titles,
                    tables=tables,
                )
            )
        return parsed_sections

    @staticmethod
    def _split_by_heading(text: str, heading_prefix: str) -> dict[str, str]:
        chunks: dict[str, list[str]] = {}
        current_heading: str | None = None
        for line in text.splitlines():
            if line.startswith(heading_prefix):
                current_heading = line[len(heading_prefix):].strip()
                chunks[current_heading] = []
                continue
            if current_heading is not None:
                chunks[current_heading].append(line)
        return {heading: "\n".join(lines).strip() for heading, lines in chunks.items()}

    def _extract_tables(self, content: str, section_title: str) -> list[MarkdownTable]:
        tables: list[MarkdownTable] = []
        lines = content.splitlines()
        index = 0
        while index < len(lines):
            if lines[index].strip().startswith("|"):
                start = index
                while index < len(lines) and lines[index].strip().startswith("|"):
                    index += 1
                table_lines = [line.strip() for line in lines[start:index] if line.strip()]
                parsed = self._parse_table_lines(table_lines)
                if parsed is not None:
                    title = self._find_table_title(lines, start, section_title)
                    tables.append(
                        MarkdownTable(
                            title=title,
                            headers=parsed[0],
                            rows=parsed[1],
                            source_section=section_title,
                        )
                    )
                continue
            index += 1
        return tables

    @staticmethod
    def _parse_table_lines(table_lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
        if len(table_lines) < 2:
            return None
        rows = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells:
                continue
            rows.append(cells)
        if len(rows) < 2:
            return None
        headers = rows[0]
        body_rows = [row for row in rows[2:] if any(cell and set(cell) != {"-"} for cell in row)]
        return headers, body_rows[:6]

    @staticmethod
    def _find_table_title(lines: list[str], start_index: int, section_title: str) -> str:
        for cursor in range(start_index - 1, max(-1, start_index - 4), -1):
            candidate = lines[cursor].strip()
            if not candidate:
                continue
            if candidate.lower().startswith("title:"):
                return candidate.split(":", 1)[1].strip()
            if not candidate.startswith("|"):
                return candidate
        return section_title

    @staticmethod
    def _paragraphs_from_text(content: str) -> list[str]:
        paragraphs: list[str] = []
        for chunk in re.split(r"\n\s*\n", content):
            normalized = " ".join(chunk.split())
            if not normalized:
                continue
            if normalized.startswith("|") or normalized.startswith("!["):
                continue
            paragraphs.append(normalized)
        return paragraphs

    def _extract_key_points(self, content: str, limit: int) -> list[str]:
        points: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("![") or stripped.startswith("|"):
                continue
            if stripped.startswith(("- ", "* ")):
                points.append(self._normalize_point(stripped[2:]))
            elif re.match(r"^\d+\.\s+", stripped):
                points.append(self._normalize_point(re.sub(r"^\d+\.\s+", "", stripped)))
            elif stripped.startswith("### "):
                points.append(self._normalize_point(stripped[4:]))
        if len(points) < limit:
            for paragraph in self._paragraphs_from_text(content):
                if paragraph.startswith("Source:"):
                    continue
                if paragraph not in points:
                    points.append(self._normalize_point(paragraph))
                if len(points) >= limit:
                    break
        return points[:limit]

    @staticmethod
    def _normalize_point(text: str) -> str:
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip(" -:")
        if len(text) > 180:
            text = text[:177].rstrip() + "..."
        return text

    def _collect_numeric_facts(self, content: str, limit: int = 20) -> list[str]:
        facts: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if len(stripped) > 220 or "data:image" in stripped:
                continue
            if any(char.isdigit() for char in stripped) and not stripped.startswith("#"):
                normalized = self._normalize_point(stripped)
                if normalized and normalized not in facts:
                    facts.append(normalized)
            if len(facts) >= limit:
                break
        return facts[:limit]

    def _dedupe_points(self, points: list[str], context: list[str] | None = None) -> list[str]:
        seen: set[str] = set()
        blocked = {self._canonicalize(text) for text in (context or []) if text}
        result: list[str] = []
        for point in points:
            normalized = self._normalize_point(point)
            canonical = self._canonicalize(normalized)
            if not normalized or canonical in seen or canonical in blocked:
                continue
            if len(canonical) < 8:
                continue
            seen.add(canonical)
            result.append(normalized)
        return result

    @staticmethod
    def _canonicalize(text: str) -> str:
        lowered = text.lower()
        lowered = re.sub(r"^\d+(\.\d+)*\s*", "", lowered)
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        return " ".join(lowered.split())
