"""Attach optional Canva design thumbnail to select blueprint slides (graphics accent)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from md2deck.canva_client import CanvaClient
from md2deck.config import AppConfig
from md2deck.models import PipelineArtifacts, VisualIntent

logger = logging.getLogger(__name__)

# Prefer visually rich intents for a small brand / mood thumbnail strip
_ENRICH_INTENTS = frozenset(
    {
        VisualIntent.ICON_FEATURE_GRID,
        VisualIntent.METRIC_GRID,
        VisualIntent.EXECUTIVE_SUMMARY,
        VisualIntent.TEXT_WITH_VISUAL,
        VisualIntent.DATA_CHART,
        VisualIntent.BULLET_LIST, # Added bullet list for more visuals
        VisualIntent.TITLE_COVER, # Added cover for visual impact
    }
)


import urllib.request
import urllib.parse
from pathlib import Path

@dataclass(slots=True)
class CanvaEnrichStage:
    name: str = "canva_enrich"

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        if artifacts.blueprint is None:
            return
            
        cache_dir = config.working_dir / "image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        design_id = (config.canva_reference_design_id or "").strip()
        canva_path = None
        
        # 1. Attempt Canva Enrichment if configured
        if design_id:
            client = CanvaClient.from_app_config(config)
            if client is not None:
                canva_path = client.download_thumbnail(design_id, cache_dir)

        assigned = 0
        for slide in artifacts.blueprint.slides:
            if slide.visual_intent not in _ENRICH_INTENTS:
                continue
            if slide.canva_thumb_path:
                continue
                
            if canva_path and canva_path.exists():
                slide.canva_thumb_path = str(canva_path)
                assigned += 1
            else:
                # 2. AI Image Generation Fallback
                try:
                    prompt = slide.title
                    if slide.summary:
                        prompt += " " + slide.summary
                    prompt = f"minimalist vector illustration for business presentation slide titled {prompt}"
                    encoded_prompt = urllib.parse.quote(prompt)
                    
                    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"
                    safe_title = "".join(c if c.isalnum() else "_" for c in slide.title)[:20]
                    img_path = cache_dir / f"slide_{safe_title}.jpg"
                    
                    if not img_path.exists():
                        urllib.request.urlretrieve(img_url, img_path)
                        
                    slide.canva_thumb_path = str(img_path)
                    assigned += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch AI image for slide {slide.title}: {e}")

            if assigned >= 25:
                break
                
        if assigned:
            logger.info("Enrich stage: attached images to %s slides", assigned)
