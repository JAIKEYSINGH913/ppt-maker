from __future__ import annotations

from dataclasses import dataclass
import json
import re

from md2deck.config import AppConfig
from md2deck.models import DeckBlueprint, PipelineArtifacts, SlideBlueprint, VisualIntent, LayoutMetadata, ThemeProfile


@dataclass(slots=True)
class BlueprintStage:
    name: str = "blueprint"

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        if artifacts.storyline is None:
            raise RuntimeError("Storyliner stage must run before blueprint generation.")

        max_words = config.visuals.max_words_per_card
        slides: list[SlideBlueprint] = []
        total_slides = len(artifacts.storyline.slides)

        for idx, story_slide in enumerate(artifacts.storyline.slides):
            # Calculate requirements for the intelligence pass
            reqs = {
                "points_count": len(story_slide.key_points or []),
                "has_picture": story_slide.visual_intent in {VisualIntent.ICON_GRID, VisualIntent.INFOGRAPHIC, VisualIntent.SWOT, VisualIntent.FUNNEL, VisualIntent.PYRAMID},
                "is_cover": idx == 0,
                "is_divider": story_slide.visual_intent == VisualIntent.SECTION_DIVIDER,
                "is_thank_you": idx == total_slides - 1 or story_slide.visual_intent == VisualIntent.THANK_YOU,
            }
            
            layout_hint = story_slide.metadata.get("layout_hint") or self._pick_optimal_layout(reqs, artifacts.theme)
            if layout_hint == "dynamic-grid":
                layout_hint = self._default_layout_hint(story_slide.visual_intent)

            table_spec = story_slide.metadata.get("table_spec") or story_slide.metadata.get("table")
            if (
                not table_spec
                and story_slide.visual_intent == VisualIntent.TABLE_FOCUS
                and artifacts.document
                and artifacts.document.tables
            ):
                t0 = artifacts.document.tables[0]
                table_spec = {
                    "title": t0.title,
                    "headers": t0.headers,
                    "rows": t0.rows[:5],
                }

            chart_spec = story_slide.metadata.get("chart_data")
            if not chart_spec and story_slide.visual_intent in {
                VisualIntent.CHART_FOCUS,
                VisualIntent.METRIC_DASHBOARD,
                VisualIntent.CHART_LINE,
            }:
                chart_spec = {
                    "categories": [re.sub(r'[^A-Za-z0-9 ]+', '', f.split(':')[0])[:15] for f in story_slide.supporting_facts[:5]],
                    "series": []
                }
                vals = []
                for f in story_slide.supporting_facts[:5]:
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", f)
                    vals.append(float(nums[0]) if nums else 0)
                chart_spec["series"] = [{"name": "Metric", "values": vals}]

            # Enforce word limit on data points
            raw_points = story_slide.key_points or story_slide.supporting_facts
            data_points = self._clean_points(story_slide.title, raw_points)[:5]
            data_points = [self._enforce_word_limit(p, max_words) for p in data_points]

            theme_tokens = {
                "primary_color": "Deep Blue" if idx % 2 == 0 else "Dark Blue",
                "accent_color": "Cyan",
                "font_style": "Minimalist Sans-Serif"
            }

            slides.append(
                SlideBlueprint(
                    title=story_slide.title,
                    summary=self._summary_for_story_slide(story_slide),
                    visual_intent=story_slide.visual_intent,
                    data_points=data_points,
                    theme_tokens=theme_tokens,
                    chart_spec=chart_spec,
                    table_spec=table_spec,
                    icon_tokens=([story_slide.metadata["icon_hint"]] if story_slide.metadata.get("icon_hint") else self._default_icon_tokens(story_slide.visual_intent, story_slide.title)),
                    layout_hint=layout_hint,
                    max_words=max_words,
                    source_slide_index=story_slide.source_slide_index,
                    user_overrides={
                        "icon_hint": story_slide.metadata.get("icon_hint"),
                        "storyteller_insight": story_slide.metadata.get("storyteller_insight"),
                    }
                )
            )

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
    def _summary_for_story_slide(story_slide) -> str:
        if story_slide.metadata.get("summary"):
            summary = story_slide.metadata["summary"]
        elif story_slide.metadata.get("agenda"):
            summary = "A structured overview of the presentation flow"
        elif story_slide.metadata.get("closing"):
            summary = "Questions & Discussion"
        elif story_slide.key_points:
            summary = story_slide.key_points[0]
        elif story_slide.supporting_facts:
            summary = story_slide.supporting_facts[0]
        else:
            summary = story_slide.narrative_goal

        # Avoid summary duplicating the title
        if BlueprintStage._canonicalize(summary) == BlueprintStage._canonicalize(story_slide.title):
            summary = story_slide.narrative_goal
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
            VisualIntent.AGENDA: ["outline", "section", "map"],
            VisualIntent.EXECUTIVE_SUMMARY_CARDS: ["insight", "growth", "risk"],
            VisualIntent.TIMELINE: ["milestone", "clock", "trend"],
            VisualIntent.COMPARISON_GRID: ["compare", "balance", "choice"],
            VisualIntent.CHEVRON_FLOW: ["step", "arrow", "decision"],
            VisualIntent.ICON_GRID: ["theme", "cluster", "signal"],
            VisualIntent.METRIC_DASHBOARD: ["metric", "trend", "benchmark"],
            VisualIntent.CHART_FOCUS: ["chart", "bar", "signal"],
            VisualIntent.TABLE_FOCUS: ["table", "grid", "evidence"],
            VisualIntent.KEY_TAKEAWAYS: ["flag", "signal", "action"],
            VisualIntent.THANK_YOU: ["conclusion", "flag", "action"],
            VisualIntent.INFOGRAPHIC: ["insight", "data", "chart"],
            VisualIntent.CLEAN_TITLE: ["innovation", "data", "insight"],
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
            VisualIntent.CLEAN_TITLE: "cover",
            VisualIntent.SECTION_DIVIDER: "dynamic-grid",
            VisualIntent.THANK_YOU: "thank_you",
        }
        return hint_map.get(intent, "dynamic-grid")
