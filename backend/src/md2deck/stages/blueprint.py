from __future__ import annotations

from dataclasses import dataclass
import json
import re

from md2deck.config import AppConfig
from md2deck.models import DeckBlueprint, PipelineArtifacts, SlideBlueprint, VisualIntent, LayoutMetadata, ThemeProfile


@dataclass
class BlueprintStage:
    name: str = "blueprint"

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        if artifacts.storyline is None:
            raise RuntimeError("Storyliner stage must run before blueprint generation.")

        max_words = config.visuals.max_words_per_card
        slides: list[SlideBlueprint] = []
        total_slides = len(artifacts.storyline.slides)
        max_layouts = len(artifacts.theme.layout_names) if artifacts.theme else 10

        # Extract theme colors as hex for the blueprint
        def to_hex(rgb): return '#%02x%02x%02x' % rgb if rgb else '#000000'
        
        c_title = to_hex(artifacts.theme.primary_color) if artifacts.theme else "#000000"
        c_body = to_hex(artifacts.theme.dark_color) if artifacts.theme else "#333333"
        c_accent = to_hex(artifacts.theme.accent_colors[0]) if artifacts.theme and artifacts.theme.accent_colors else "#7F3FFF"

        for i, story_slide in enumerate(artifacts.storyline.slides):
            intent = getattr(story_slide, 'visual_intent', VisualIntent.BULLET_LIST)
            layout_idx = 1 # Default middle layout
            
            # 1. Front Slide: Title (2-5 words) and Description (2-3 lines)
            if i == 0:
                intent = VisualIntent.TITLE_COVER
                layout_idx = 0 # Explicitly use first layout for cover
                title = BlueprintStage._enforce_word_limit(getattr(story_slide, 'title', 'Presentation'), 5)
                summary = self._summary_for_story_slide(story_slide)
                summary = BlueprintStage._enforce_word_limit(summary, 30) # ~2-3 lines
                data_points = []
            
            # 2. Last Slide: Thank You (No text)
            elif i == total_slides - 1:
                intent = VisualIntent.THANK_YOU
                title = "" # No text on thank you slide
                summary = ""
                data_points = []
                # Resolve Thank You index (usually last)
                if artifacts.theme:
                    layout_idx = max_layouts - 1
                    for l_idx, m in artifacts.theme.layouts_metadata.items():
                        if "thank" in m.name.lower():
                            layout_idx = l_idx
                            break
            
            # 3. Middle Slides: Interactive elements and middle layouts only
            else:
                title = BlueprintStage._enforce_word_limit(getattr(story_slide, 'title', 'Untitled'), 4)
                # UNIVERSAL DATA EXTRACTION (bullets, key_points, etc)
                raw_points = (
                    getattr(story_slide, 'key_points', []) or 
                    getattr(story_slide, 'supporting_facts', []) or 
                    getattr(story_slide, 'bullets', []) or
                    story_slide.metadata.get('bullets', []) or
                    story_slide.metadata.get('data', {}).get('bullets', []) or
                    story_slide.metadata.get('key_points', [])
                )
                data_points = self._clean_points(title, raw_points)[:6]
                data_points = [self._enforce_word_limit(p, 35) for p in data_points]
                summary = self._enforce_word_limit(self._summary_for_story_slide(story_slide), 50)
                
                # Layout restriction: AVOID index 0 (cover) and max_layouts-1 (thank you)
                source_idx = getattr(story_slide, 'source_slide_index', None)
                if source_idx is not None and 1 <= source_idx < max_layouts - 1:
                    layout_idx = source_idx
                else:
                    # Fallback to a middle layout if source_idx was invalid or cover/thankyou
                    layout_idx = 1 if max_layouts > 1 else 0

            slide_metadata = getattr(story_slide, 'metadata', {})
            blueprint_slide = SlideBlueprint(
                title=title,
                summary=summary,
                data_points=data_points,
                visual_intent=intent,
                source_slide_index=layout_idx,
                icon_tokens=[slide_metadata.get('icon_hint', '')] if slide_metadata.get('icon_hint', '') else [],
                table_spec=slide_metadata.get('table_spec'),
                chart_spec=slide_metadata.get('chart_data'),
                title_color=c_title,
                body_color=c_body,
                accent_color=c_accent,
                meta={
                    "original_index": i,
                    "storyteller_insight": slide_metadata.get('summary', '')
                }
            )
            slides.append(blueprint_slide)

        artifacts.blueprint = DeckBlueprint(
            deck_title=artifacts.storyline.deck_title,
            slides=slides,
        )

        # Persistence: Save the blueprint for validation/editability in the universal format
        try:
            blueprint_path = config.working_dir / "slide_blueprint.json"
            theme_id = artifacts.theme.layout_names[0].split("_")[0] if artifacts.theme and artifacts.theme.layout_names else "THEME_1"
            universal_data = artifacts.blueprint.to_universal_dict(theme_id=theme_id)
            
            with open(blueprint_path, "w", encoding="utf-8") as f:
                json.dump(universal_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save slide_blueprint.json: {e}")

    @staticmethod
    def _chart_spec_from_text_lines(lines: list[str]) -> dict | None:
        """Build minimal chart spec from bullet lines when numeric facts are missing."""
        labels: list[str] = []
        values: list[float] = []
        for line in lines[:5]:
            if not line:
                continue
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(line))
            if not nums:
                continue
            lab = re.sub(r"[-+]?\d*\.\d+|\d+", "", str(line))
            lab = re.sub(r"[^A-Za-z0-9 ]+", " ", lab).strip()[:18] or f"Item {len(labels)+1}"
            labels.append(lab)
            try:
                values.append(float(nums[0].replace(",", "")))
            except ValueError:
                values.append(0.0)
        if len(labels) < 2:
            return None
        return {"labels": labels, "values": values}

    @staticmethod
    def _summary_for_story_slide(story_slide: Any) -> str:
        metadata = getattr(story_slide, 'metadata', {})
        if metadata.get("summary"):
            summary = metadata["summary"]
        elif metadata.get("agenda"):
            summary = "A structured overview of the presentation flow"
        elif metadata.get("closing"):
            summary = "Questions & Discussion"
        elif getattr(story_slide, 'key_points', []):
            summary = getattr(story_slide, 'key_points')[0]
        elif getattr(story_slide, 'supporting_facts', []):
            summary = getattr(story_slide, 'supporting_facts')[0]
        else:
            summary = getattr(story_slide, 'narrative_goal', 'Focus on key insights.')
        # Avoid summary duplicating the title
        title = getattr(story_slide, 'title', '')
        if BlueprintStage._canonicalize(summary) == BlueprintStage._canonicalize(title):
            summary = getattr(story_slide, 'narrative_goal', 'Key takeaways')
        return summary[:140]

    @staticmethod
    def _clean_points(title: str, points: list[str]) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()
        blocked = {BlueprintStage._canonicalize(title)}
        for point in points:
            normalized = " ".join(point.split()).strip()
            canonical = BlueprintStage._canonicalize(normalized)
            if not normalized or canonical in blocked or canonical in seen:
                continue
            seen.add(canonical)
            results.append(normalized)
        return results

    @staticmethod
    def _enforce_word_limit(text: str, max_words: int = 35) -> str:
        """Truncate text to max words and add ellipsis if needed."""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "…"

    @staticmethod
    def _canonicalize(text: str) -> str:
        lowered = text.lower()
        lowered = re.sub(r"^\d+(\.\d+)*\s*", "", lowered)
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        return " ".join(lowered.split())

    @staticmethod
    def _default_icon_tokens(intent: VisualIntent, title: str = "") -> list[str]:
        """Generate contextual icon tokens based on visual intent and slide title."""
        icon_map = {
            VisualIntent.TITLE_COVER: ["innovation", "data", "insight"],
            VisualIntent.EXECUTIVE_SUMMARY: ["insight", "growth", "risk"],
            VisualIntent.BULLET_LIST: ["outline", "section", "map"],
            VisualIntent.SECTION_DIVIDER: ["step", "arrow", "decision"],
            VisualIntent.ICON_FEATURE_GRID: ["theme", "cluster", "signal"],
            VisualIntent.METRIC_GRID: ["metric", "trend", "benchmark"],
            VisualIntent.DATA_CHART: ["chart", "bar", "signal"],
            VisualIntent.DATA_TABLE: ["table", "grid", "evidence"],
            VisualIntent.THANK_YOU: ["conclusion", "flag", "action"],
        }

        base_tokens = icon_map.get(intent, [])

        # Extract context-relevant tokens from title
        title_lower = title.lower()
        context_map = {
            "market": "market", "finance": "finance", "energy": "energy",
            "health": "health", "tech": "tech", "digital": "digital",
            "ai": "tech", "solar": "energy", "bank": "finance",
            "invest": "finance", "global": "global", "research": "research",
            "sustain": "sustainability", "innovat": "innovation",
            "security": "security", "educat": "education",
        }
        for keyword, token in context_map.items():
            if keyword in title_lower and token not in base_tokens:
                base_tokens = [token] + base_tokens[:2]
                break

        return base_tokens[:3] if base_tokens else ["insight", "data", "trend"]

    def _pick_optimal_layout(self, slide_reqs: dict, theme: ThemeProfile | None) -> str:
        """Find the best-fit layout name by scoring available layouts against requirements."""
        if not theme or not theme.layouts_metadata:
            return "dynamic-grid"
            
        best_layout = "dynamic-grid"
        best_score = -1
        
        for meta in theme.layouts_metadata.values():
            score = 0
            # Basic type matching
            if slide_reqs.get("is_cover") and "title" in meta.name and "slide" in meta.name: score += 50
            if slide_reqs.get("is_divider") and "section" in meta.name: score += 50
            if slide_reqs.get("is_thank_you") and "thank" in meta.name: score += 50
            
            # Placeholder capacity matching
            points_count = slide_reqs.get("points_count", 0)
            available_bodies = len(meta.body_slots)
            if points_count > 0:
                if available_bodies >= 1: score += 10
                if available_bodies >= points_count: score += 5 # Bonus for enough slots
            
            has_picture = slide_reqs.get("has_picture", False)
            available_pics = len(meta.picture_slots)
            if has_picture and available_pics >= 1:
                score += 20
            
            if score > best_score:
                best_score = score
                best_layout = meta.name
                
        return best_layout

    @staticmethod
    def _default_layout_hint(intent: VisualIntent) -> str:
        hint_map = {
            VisualIntent.TITLE_COVER: "cover",
            VisualIntent.SECTION_DIVIDER: "divider",
            VisualIntent.THANK_YOU: "thank_you",
            VisualIntent.BULLET_LIST: "content",
        }
        return hint_map.get(intent, "dynamic-grid")
        hint_map = {
            VisualIntent.TITLE_COVER: "cover",
            VisualIntent.SECTION_DIVIDER: "divider",
            VisualIntent.THANK_YOU: "thank_you",
            VisualIntent.BULLET_LIST: "content",
        }
        return hint_map.get(intent, "dynamic-grid")
