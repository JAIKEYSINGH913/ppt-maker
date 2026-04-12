"""Per-master geometry: insets clear fixed brand art (corners differ by template). Tune after visual QA."""
from __future__ import annotations

from dataclasses import dataclass

from md2deck.models import MasterLayoutProfile


def geometry_for_master_name(master_name_lower: str) -> MasterLayoutProfile:
    """Return layout profile for one of the three Slide Master decks (filename stem match)."""
    if "accenture" in master_name_lower:
        # Centered brand; reserve top title band + bottom footer ribbon
        return MasterLayoutProfile(
            blank_inset_top=0.72,
            blank_inset_right=0.55,
            blank_inset_bottom=0.95,
            blank_inset_left=0.55,
            footer_reserve_inches=0.62,
            hero_title_max_chars=44,
            hero_title_pt=34,
            icon_margin_top=0.42,
            icon_margin_right=0.48,
        )
    if "ai bubble" in master_name_lower or "bubble" in master_name_lower:
        # Navy header strip; keep body below typical title zone
        return MasterLayoutProfile(
            blank_inset_top=0.78,
            blank_inset_right=0.52,
            blank_inset_bottom=0.88,
            blank_inset_left=0.42,
            footer_reserve_inches=0.60,
            hero_title_max_chars=48,
            hero_title_pt=32,
            icon_margin_top=0.38,
            icon_margin_right=0.45,
        )
    if "uae" in master_name_lower or "solar" in master_name_lower:
        # Green bands / lower subtitle lane — extra bottom clearance
        return MasterLayoutProfile(
            blank_inset_top=0.58,
            blank_inset_right=0.50,
            blank_inset_bottom=1.05,
            blank_inset_left=0.48,
            footer_reserve_inches=0.68,
            hero_title_max_chars=42,
            hero_title_pt=30,
            icon_margin_top=0.36,
            icon_margin_right=0.50,
        )
    return MasterLayoutProfile()
