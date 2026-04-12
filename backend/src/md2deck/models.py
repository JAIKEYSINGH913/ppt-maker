from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class VisualIntent(StrEnum):
    CLEAN_TITLE = "clean-title"
    AGENDA = "agenda"
    EXECUTIVE_SUMMARY_CARDS = "executive-summary-cards"
    SECTION_DIVIDER = "chevron-flow"  # Often used as progress flow
    TIMELINE = "timeline"
    COMPARISON_GRID = "comparison-table"
    METRIC_DASHBOARD = "metric-dashboard"
    PROCESS_FLOW = "process-flow"
    ICON_CLUSTER = "icon-grid"
    CHART_FOCUS = "chart-bar"
    TABLE_FOCUS = "comparison-table"
    KEY_TAKEAWAYS = "key-takeaways"
    THANK_YOU = "thank-you"
    CHART_LINE = "chart-line"
    CHEVRON_FLOW = "chevron-flow"
    ICON_GRID = "icon-grid"
    INFOGRAPHIC = "infographic"
    SWOT = "swot"
    FUNNEL = "funnel"
    PYRAMID = "pyramid"


@dataclass(slots=True)
class MarkdownTable:
    title: str
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    source_section: str = ""


@dataclass(slots=True)
class MarkdownSection:
    title: str
    level: int
    body: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    numeric_facts: list[str] = field(default_factory=list)
    subsection_titles: list[str] = field(default_factory=list)
    tables: list[MarkdownTable] = field(default_factory=list)


@dataclass(slots=True)
class MarkdownDocument:
    path: Path
    raw_text: str
    cleaned_text: str = ""
    title: str | None = None
    subtitle: str = ""
    executive_summary: list[str] = field(default_factory=list)
    sections: list[MarkdownSection] = field(default_factory=list)
    tables: list[MarkdownTable] = field(default_factory=list)
    numeric_facts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StorySlide:
    title: str
    narrative_goal: str
    visual_intent: VisualIntent
    key_points: list[str] = field(default_factory=list)
    supporting_facts: list[str] = field(default_factory=list)
    source_section: str = ""
    source_slide_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Storyline:
    deck_title: str
    slide_target: int
    slides: list[StorySlide] = field(default_factory=list)


@dataclass(slots=True)
class SlideBlueprint:
    title: str
    summary: str = ""
    visual_intent: VisualIntent = VisualIntent.CLEAN_TITLE
    data_points: list[str] = field(default_factory=list)
    theme_tokens: dict[str, Any] = field(default_factory=dict)
    chart_spec: dict[str, Any] | None = None
    table_spec: dict[str, Any] | None = None
    icon_tokens: list[str] = field(default_factory=list)
    icon_paths: list[str] = field(default_factory=list)
    canva_thumb_path: str | None = None
    layout_hint: str | None = None
    max_words: int = 35
    user_overrides: dict[str, Any] = field(default_factory=dict)
    rendered_layout_index: int | None = None
    source_slide_index: int | None = None


@dataclass(slots=True)
class DeckBlueprint:
    deck_title: str
    slides: list[SlideBlueprint] = field(default_factory=list)

    def to_universal_dict(self, theme_id: str = "THEME_1") -> dict[str, Any]:
        """Convert to the user's requested 'Universal JSON Format'."""
        universal_slides = []
        for i, slide in enumerate(self.slides):
            # Determine type and template
            if slide.visual_intent == VisualIntent.CLEAN_TITLE:
                s_type = "title"
                template = "TITLE_SLIDE"
                data = {
                    "title": slide.title,
                    "subtitle": slide.summary
                }
            elif slide.visual_intent in {
                VisualIntent.TIMELINE, VisualIntent.ICON_GRID, VisualIntent.SWOT, 
                VisualIntent.FUNNEL, VisualIntent.PYRAMID, VisualIntent.CHART_FOCUS,
                VisualIntent.CHEVRON_FLOW, VisualIntent.ICON_CLUSTER
            }:
                s_type = "split"
                template = "SPLIT_SLIDE"
                # Map visual intent to a friendly visual name
                visual_name = slide.visual_intent.value.replace("-", "_")
                data = {
                    "title": slide.title,
                    "left_bullets": slide.data_points[:5],
                    "right_visual": visual_name
                }
            else:
                s_type = "content"
                template = "CONTENT_SLIDE"
                data = {
                    "title": slide.title,
                    "bullets": slide.data_points[:5]
                }

            universal_slides.append({
                "id": i + 1,
                "type": s_type,
                "template": template,
                "data": data
            })

        return {
            "theme": theme_id,
            "meta": {
                "title": self.deck_title,
                "total_slides": len(universal_slides),
                "version": "1.0"
            },
            "slides": universal_slides
        }


@dataclass(slots=True)
class SlotMetadata:
    """Dimensions and type of a layout placeholder."""
    type: str  # e.g., "title", "body", "picture"
    left: int
    top: int
    width: int
    height: int


@dataclass(slots=True)
class MasterLayoutProfile:
    """Theme-specific safe area for Blank slides (inches from slide edges unless noted)."""
    blank_inset_top: float = 0.60
    blank_inset_right: float = 0.50
    blank_inset_bottom: float = 0.85
    blank_inset_left: float = 0.50
    footer_reserve_inches: float = 0.65  # storyteller + slide number above bottom inset
    hero_title_max_chars: int = 52
    hero_title_pt: int = 32
    icon_margin_top: float = 0.36
    icon_margin_right: float = 0.46


@dataclass(slots=True)
class LayoutMetadata:
    """Extracted structure of a single slide layout."""
    name: str
    index: int
    has_title: bool = False
    has_subtitle: bool = False
    body_slots: list[SlotMetadata] = field(default_factory=list)
    picture_slots: list[SlotMetadata] = field(default_factory=list)
    
    # Bounding box of all content placeholders (the "Safe Zone")
    safe_rect: tuple[int, int, int, int] | None = None 


@dataclass(slots=True)
class SlideContentMetadata:
    """Analysis of an existing slide in a template deck."""
    index: int
    layout_name: str
    texts: list[str]
    tables: list[list[list[str]]] # Table -> Row -> Cell
    shape_count: int


@dataclass(slots=True)
class ThemeProfile:
    master_path: Path
    slide_width: int
    slide_height: int
    layout_names: list[str]
    layouts_metadata: dict[int, LayoutMetadata] = field(default_factory=dict)
    primary_color: tuple[int, int, int] = (11, 78, 161)
    accent_colors: list[tuple[int, int, int]] = field(default_factory=list)
    light_colors: list[tuple[int, int, int]] = field(default_factory=list)
    dark_color: tuple[int, int, int] = (15, 23, 42)
    muted_color: tuple[int, int, int] = (100, 116, 139)
    theme_notes: dict[str, Any] = field(default_factory=dict)
    design_dna: dict[str, Any] = field(default_factory=dict)
    geometry: MasterLayoutProfile | None = None
    template_dna: list[SlideContentMetadata] = field(default_factory=list)


@dataclass(slots=True)
class SlidePreview:
    """Serializable preview of a single slide for the frontend carousel."""
    index: int
    title: str
    summary: str
    visual_intent: str
    data_points: list[str]
    icon_tokens: list[str]
    layout_hint: str
    has_chart: bool = False
    has_table: bool = False
    background_url: str | None = None
    overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "summary": self.summary,
            "visual_intent": self.visual_intent,
            "data_points": self.data_points,
            "icon_tokens": self.icon_tokens,
            "layout_hint": self.layout_hint,
            "has_chart": self.has_chart,
            "has_table": self.has_table,
            "background_url": self.background_url,
            "overrides": self.overrides,
        }


@dataclass(slots=True)
class PipelineArtifacts:
    document: MarkdownDocument | None = None
    storyline: Storyline | None = None
    blueprint: DeckBlueprint | None = None
    theme: ThemeProfile | None = None
    validation_notes: list[str] = field(default_factory=list)

    def get_slide_previews(self, template_id: str | None = None) -> list[dict[str, Any]]:
        """Generate preview data from blueprint for the frontend carousel."""
        if self.blueprint is None:
            return []
        previews = []
        for idx, slide in enumerate(self.blueprint.slides):
            # Resolve background image from the actual layout used
            l_idx = slide.rendered_layout_index if slide.rendered_layout_index is not None else idx
            bg = f"/thumbnails/{template_id}/slide_{l_idx}.png" if template_id else None
            
            previews.append(SlidePreview(
                index=idx,
                title=slide.title,
                summary=slide.summary,
                visual_intent=slide.visual_intent.value,
                data_points=slide.data_points,
                icon_tokens=slide.icon_tokens,
                layout_hint=slide.layout_hint or "dynamic-grid",
                has_chart=slide.chart_spec is not None,
                has_table=slide.table_spec is not None,
                background_url=bg,
                overrides=slide.user_overrides,
            ).to_dict())
        return previews
