import os
import json
import re
import logging
import google.generativeai as genai
from dataclasses import dataclass

from md2deck.config import AppConfig
from md2deck.models import PipelineArtifacts, StorySlide, Storyline, VisualIntent, SlideContentMetadata

logger = logging.getLogger(__name__)

class GeminiNarrator:
    """AI Agent to process raw markdown into a complete slide-by-slide storyline."""
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.enabled = bool(self.api_key)
        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                # Using 1.5 pro to handle potentially large markdown files accurately
                self.model = genai.GenerativeModel("gemini-1.5-pro")
                logger.info("GeminiNarrator initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
                self.enabled = False

    def generate_full_storyline(self, raw_content: str, min_slides: int, max_slides: int, template_dna: list = None) -> dict:
        if not self.enabled:
            return {}
        
        dna_str = ""
        if template_dna:
            dna_str = "EXISTING TEMPLATE SLIDES (Source Slides):\n"
            for s in template_dna:
                content_preview = ", ".join(s.texts)[:400]
                dna_str += f"- Slide {s.index} (Layout: {s.layout_name}): Contents: [{content_preview}]\n"

        prompt = f"""
        You are an Executive Presentation Architect. 
        Transform the following raw markdown content into a high-fidelity slide blueprint.

        {dna_str}

        GOALS:
        1. SEMANTIC MAPPING: Map your slides to the EXISTING TEMPLATE SLIDES provided above. 
           If Slide 3 in the template is a table and you have tabular data, use `"source_slide_index": 3`.
           DO NOT replace Slide 3 with a bullet list if Slide 3 is a table; find the best matching source slide.
        2. CLEAN TEXT: REMOVE ALL MARKDOWN SYMBOLS (###, **, -, etc). Plain English only.
        3. BREVITY: Max 12 words per summary, max 8 words per bullet.
        4. TARGET LENGTH: Generate {min_slides} to {max_slides} slides based on content.

        INPUT CONTENT:
        {raw_content[:25000]}

        OUTPUT FORMAT:
        You MUST respond ONLY with a valid JSON object matching this schema:
        {{
          "deck_title": "Presentation Title",
          "slides": [
            {{
              "title": "Slide Title",
              "summary": "Impactful summary",
              "data_points": ["Point 1", "Point 2"],
              "visual_intent": "clean-title|agenda|metric-dashboard|chart-bar|comparison-table|icon-grid|timeline|swot|key-takeaways|thank-you|chevron-flow",
              "source_slide_index": 0, // The index (from DNA) of the template slide to clone.
              "icon_hint": "rocket",
              "table_spec": {{ "headers": ["Col 1", "Col 2"], "rows": [["V1", "V2"]] }}, // If template slide is a table
              "chart_data": {{ "categories": ["A", "B"], "series": [{{ "name": "Sales", "values": [10, 20] }}] }} // If template slide is a chart
            }}
          ]
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"Gemini full storyline generation failed: {e}")
        return {}


@dataclass(slots=True)
class StorylinerStage:
    name: str = "storyliner"
    narrator: GeminiNarrator = None

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        if artifacts.document is None:
            raise RuntimeError("Ingest stage must run before storyline generation.")
 
        self.narrator = GeminiNarrator()
        raw_text = artifacts.document.cleaned_text or artifacts.document.raw_text

        slides: list[StorySlide] = []
        deck_title = artifacts.document.title or config.input_markdown.stem

        if self.narrator.enabled:
            # Generate the entire storyline natively via AI
            result = self.narrator.generate_full_storyline(
                raw_text, 
                config.constraints.min_slides, 
                config.constraints.max_slides,
                template_dna=artifacts.theme.template_dna if artifacts.theme else None
            )
            if result and "slides" in result:
                deck_title = re.sub(r'[*#_`]', '', result.get("deck_title", deck_title)).strip()
                for slide_data in result["slides"]:
                    intent_str = slide_data.get("visual_intent", "chevron-flow")
                    try:
                        intent = VisualIntent(intent_str)
                    except ValueError:
                        intent = VisualIntent.CHEVRON_FLOW

                    cleaned_title = re.sub(r'[*#_`]', '', slide_data.get("title", "Untitled Slide")).strip()
                    cleaned_summary = re.sub(r'[*#_`]', '', slide_data.get("summary", "")).strip()
                    cleaned_points = [re.sub(r'[*#_`]', '', pt).strip() for pt in slide_data.get("data_points", [])]

                    # Transform chart_data object properly to tuple lists if necessary, or pass through via metadata
                    meta = {
                        "summary": cleaned_summary,
                        "icon_hint": slide_data.get("icon_hint", ""),
                        "storyteller_insight": slide_data.get("storyteller_insight", "")
                    }
                    if "chart_data" in slide_data:
                        meta["chart_data"] = slide_data["chart_data"]
                    if "table_spec" in slide_data:
                        meta["table_spec"] = slide_data["table_spec"]

                    slides.append(
                        StorySlide(
                            title=cleaned_title,
                            narrative_goal="Distill this section into a single clear visual message.",
                            visual_intent=intent,
                            key_points=cleaned_points,
                            source_slide_index=slide_data.get("source_slide_index"),
                            metadata=meta
                        )
                    )
        
        # Fallback if Gemini is disabled or fails
        if not slides:
            logger.warning("Fell back to basic parser because AI generation failed or is disabled.")
            slides.append(
                StorySlide(
                    title=deck_title,
                    narrative_goal="Introduce the topic.",
                    visual_intent=VisualIntent.CLEAN_TITLE,
                    key_points=[],
                )
            )
            for section in artifacts.document.sections[:config.constraints.max_slides - 2]:
                slides.append(
                    StorySlide(
                        title=section.title,
                        narrative_goal="Present findings",
                        visual_intent=VisualIntent.CHEVRON_FLOW,
                        key_points=(section.bullets or section.body)[:4]
                    )
                )
            slides.append(
                StorySlide(
                    title="Thank You",
                    narrative_goal="Close presentation.",
                    visual_intent=VisualIntent.THANK_YOU,
                    key_points=["Questions & Discussion"],
                    metadata={"closing": True}
                )
            )

        artifacts.storyline = Storyline(deck_title=deck_title, slide_target=len(slides), slides=slides)
