from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DeckConstraints:
    min_slides: int = 5
    max_slides: int = 15
    max_markdown_size_mb: int = 5


@dataclass(slots=True)
class VisualSystemConfig:
    infographic_first: bool = True
    icons_enabled: bool = True
    charts_enabled: bool = True
    tables_enabled: bool = True
    visual_storytelling_enabled: bool = True
    max_bullets_per_slide: int = 4
    max_words_per_slide: int = 80
    max_words_per_card: int = 35
    max_lines_per_block: int = 6
    preferred_visual_intents: list[str] = field(
        default_factory=lambda: [
            "hero_cover",
            "agenda",
            "executive_summary_cards",
            "section_divider",
            "timeline",
            "comparison_grid",
            "metric_dashboard",
            "process_flow",
            "chart_focus",
            "table_focus",
            "key_takeaways",
            "thank_you",
            "pyramid",
            "funnel",
            "swot",
            "cycle",
        ]
    )

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

FREEPIK_API_KEY = os.environ.get("FREEPIK_API_KEY", "")

# Canva Connect API credentials (OAuth2 PKCE flow)
CANVA_CLIENT_ID = os.environ.get("CANVA_CLIENT_ID", "")
CANVA_CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET", "")
CANVA_REFRESH_TOKEN = os.environ.get("CANVA_REFRESH_TOKEN", "")
# Optional: Canva design ID (from design URL) to pull a thumbnail strip for graphics-heavy slides
CANVA_REFERENCE_DESIGN_ID = os.environ.get("CANVA_REFERENCE_DESIGN_ID", "")

@dataclass(slots=True)
class AnimationConfig:
    """Controls PPTX slide transition and shape animation injection."""
    transitions_enabled: bool = True
    entrance_animations_enabled: bool = True
    default_transition_speed: str = "med"  # slow, med, fast
    default_animation_duration_ms: int = 600


@dataclass(slots=True)
class AppConfig:
    input_markdown: Path
    master_pptx: Path
    output_pptx: Path
    working_dir: Path
    constraints: DeckConstraints = field(default_factory=DeckConstraints)
    visuals: VisualSystemConfig = field(default_factory=VisualSystemConfig)
    animations: AnimationConfig = field(default_factory=AnimationConfig)
    freepik_api_key: str = FREEPIK_API_KEY
    canva_client_id: str = CANVA_CLIENT_ID
    canva_client_secret: str = CANVA_CLIENT_SECRET
    canva_refresh_token: str = CANVA_REFRESH_TOKEN
    canva_reference_design_id: str = CANVA_REFERENCE_DESIGN_ID
