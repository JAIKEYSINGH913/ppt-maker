import os
import json
import re
import logging
import httpx
from dataclasses import dataclass
from typing import Optional, List

from md2deck.config import AppConfig
from md2deck.models import PipelineArtifacts, StorySlide, Storyline, VisualIntent

logger = logging.getLogger(__name__)

class OllamaNarrator:
    """Local Ollama-powered narrator for free, private slide generation."""
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.base_url = os.getenv("OLLAMA_BASE_URL", base_url).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", model)
        self.enabled = self._check_connection()

    def _check_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except: return False

    def generate_full_storyline(self, raw_content: str, min_slides: int, max_slides: int) -> dict:
        if not self.enabled: return {}
        
        prompt = f"""
        TASK: Transform raw markdown into a high-fidelity slide blueprint.
        
        CONSTRAINTS (STRICT):
        1. FIRST SLIDE (COVER): 
           - Title MUST BE 2-5 words ONLY.
           - Summary MUST BE exactly 2 lines (max 15 words total).
        2. THANK YOU SLIDE: 
           - ALWAYS the final slide. 
           - Title "Thank You". 
           - NO bullets or summary allowed.
        3. MIDDLE SLIDES:
           - Titles: 1-4 words ONLY.
           - visual_intent: Choose from [title-cover, bullet-list, data-table, data-chart, thank-you].
           - If data-table: Provide "table_data": {{"headers": ["Col1", "Col2"], "rows": [["R1C1", "R1C2"], ["R2C1", "R2C2"]]}}.
           - If data-chart: Provide "chart_data": [["Item A", 45], ["Item B", 32]].
        
        INPUT CONTENT:
        {raw_content[:10000]}
        
        TARGET: {min_slides} to {max_slides} slides.
        
        OUTPUT FORMAT (GENERATE ONLY VALID JSON):
        {{
          "deck_title": "...",
          "slides": [
            {{
              "title": "...",
              "summary": "Impactful contextual description",
              "bullets": ["...", "..."],
              "visual_intent": "...",
              "table_data": null,
              "chart_data": null
            }}
          ]
        }}
        """
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
            resp = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=90.0)
            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "{}")
                if isinstance(raw_response, str):
                    # Robust extraction
                    match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                    return json.loads(match.group()) if match else json.loads(raw_response)
                return raw_response
        except Exception as e:
            logger.warning(f"Ollama generation failed: {e}")
        return {}

@dataclass
class StorylinerStage:
    name: str = "storyliner"
    
    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        if artifacts.document is None:
            raise RuntimeError("Ingest stage must run before storyline generation.")

        raw_text = artifacts.document.cleaned_text or artifacts.document.raw_text
        slides: list[StorySlide] = []
        deck_title = artifacts.document.title or config.input_markdown.stem

        ollama = OllamaNarrator()
        result = {}
        
        if ollama.enabled:
            logger.info(f"Using Local Ollama Narrator ({ollama.model})")
            result = ollama.generate_full_storyline(raw_text, config.constraints.min_slides, config.constraints.max_slides)
        else:
            logger.warning("Ollama not found. Falling back to basic parser.")

        if result and "slides" in result:
            deck_title = result.get("deck_title", deck_title)
            for s in result["slides"]:
                slides.append(StorySlide(
                    title=s.get("title", "Untitled"),
                    narrative_goal="Distill message.",
                    visual_intent=VisualIntent(s.get("visual_intent", "bullet-list")),
                    key_points=s.get("bullets", []) or s.get("data_points", []),
                    metadata={
                        "summary": s.get("summary", ""), 
                        "bullets": s.get("bullets", []),
                        "table_data": s.get("table_data"),
                        "chart_data": s.get("chart_data")
                    }
                ))
        
        # Fallback if AI fails
        if not slides:
            logger.warning("Fell back to simple parser because AI generation failed.")
            slides.append(StorySlide(
                title=deck_title,
                narrative_goal="Intro",
                visual_intent=VisualIntent.TITLE_COVER,
                metadata={"summary": artifacts.document.subtitle or "Overview", "is_cover": True}
            ))
            for section in artifacts.document.sections[:config.constraints.max_slides - 2]:
                slides.append(StorySlide(
                    title=section.title,
                    narrative_goal="Content",
                    visual_intent=VisualIntent.BULLET_LIST,
                    key_points=(section.bullets or section.body)[:4]
                ))
            slides.append(StorySlide(
                title="Thank You",
                narrative_goal="Closing",
                visual_intent=VisualIntent.THANK_YOU,
                metadata={"closing": True}
            ))

        artifacts.storyline = Storyline(deck_title=deck_title, slide_target=len(slides), slides=slides)
        logger.info(f"Storyline ready with {len(slides)} slides.")
