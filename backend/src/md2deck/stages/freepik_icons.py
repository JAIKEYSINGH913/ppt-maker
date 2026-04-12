"""Freepik API integration for fetching high-quality icons to embed in PPTX slides."""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FREEPIK_BASE = "https://api.freepik.com/v1"

# Cache downloaded icons to avoid re-downloading
_icon_cache: dict[str, Path] = {}


@dataclass(slots=True)
class FreepikIcon:
    icon_id: int
    description: str
    preview_url: str
    local_path: Path | None = None


def search_icons(api_key: str, query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search Freepik for icons matching a keyword query."""
    if not api_key:
        logger.warning("No Freepik API key provided, skipping icon search.")
        return []
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{FREEPIK_BASE}/icons",
                params={"term": query, "per_page": limit, "shape": "fill"},
                headers={"x-freepik-api-key": api_key, "Accept": "application/json"},
            )
            if response.status_code != 200:
                logger.warning(f"Freepik API returned {response.status_code} for query '{query}'")
                return []
            data = response.json()
            return data.get("data", [])[:limit]
    except Exception as e:
        logger.warning(f"Freepik icon search failed for '{query}': {e}")
        return []


def download_icon(api_key: str, icon_id: int, cache_dir: Path, fmt: str = "png", size: int = 256) -> Path | None:
    """Download a specific icon by ID and save it to cache_dir. Returns local path."""
    cache_key = f"{icon_id}_{fmt}_{size}"
    if cache_key in _icon_cache and _icon_cache[cache_key].exists():
        return _icon_cache[cache_key]

    cache_dir.mkdir(parents=True, exist_ok=True)
    local_path = cache_dir / f"icon_{icon_id}_{size}.{fmt}"

    if local_path.exists():
        _icon_cache[cache_key] = local_path
        return local_path

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{FREEPIK_BASE}/icons/{icon_id}/download",
                params={"format": fmt, "png_size": size},
                headers={"x-freepik-api-key": api_key, "Accept": "application/json"},
            )
            if response.status_code != 200:
                logger.warning(f"Freepik icon download failed for ID {icon_id}: {response.status_code}")
                return None

            download_data = response.json()
            download_url = download_data.get("data", {}).get("url")
            if not download_url:
                logger.warning(f"No download URL in Freepik response for icon {icon_id}")
                return None

            # Download the actual image
            img_response = client.get(download_url)
            if img_response.status_code != 200:
                logger.warning(f"Failed to download icon image from {download_url}")
                return None

            local_path.write_bytes(img_response.content)
            _icon_cache[cache_key] = local_path
            logger.info(f"Downloaded Freepik icon {icon_id} to {local_path}")
            return local_path

    except Exception as e:
        logger.warning(f"Freepik icon download failed for ID {icon_id}: {e}")
        return None


def fetch_icons_for_tokens(api_key: str, tokens: list[str], cache_dir: Path) -> list[Path]:
    """Given a list of keyword tokens, search + download icons for each.

    Returns list of local file paths (may contain None entries for failures).
    """
    paths: list[Path] = []
    for token in tokens[:4]:  # Limit to 4 icons per slide max
        results = search_icons(api_key, token, limit=1)
        if results:
            icon_data = results[0]
            icon_id = icon_data.get("id")
            if icon_id:
                path = download_icon(api_key, icon_id, cache_dir)
                if path:
                    paths.append(path)
                    continue
        # Fallback: no icon found for this token
        logger.info(f"No Freepik icon found for token '{token}', will use shape fallback.")
    return paths


# Unicode fallback icons when Freepik is unavailable
UNICODE_ICON_MAP: dict[str, str] = {
    "insight": "◆",
    "growth": "▲",
    "risk": "⚠",
    "trend": "📈",
    "action": "▶",
    "milestone": "◎",
    "clock": "⏱",
    "compare": "⇋",
    "balance": "⚖",
    "choice": "◇",
    "step": "①",
    "arrow": "➤",
    "decision": "✦",
    "theme": "★",
    "cluster": "✿",
    "signal": "◉",
    "metric": "📊",
    "benchmark": "📏",
    "chart": "📈",
    "bar": "▮",
    "table": "▦",
    "grid": "⊞",
    "evidence": "📋",
    "flag": "🚩",
    "outline": "☰",
    "section": "§",
    "map": "🗺",
    "core": "◉",
    "process": "⟳",
    "strategy": "♟",
    "framework": "⬡",
    "data": "⊟",
    "analysis": "🔍",
    "market": "🏪",
    "finance": "💰",
    "energy": "⚡",
    "health": "❤",
    "tech": "⚙",
    "global": "🌐",
    "research": "🔬",
    "innovation": "💡",
    "sustainability": "♻",
    "digital": "💻",
    "security": "🛡",
    "education": "📚",
    "summary": "📝",
    "conclusion": "✔",
    "recommendation": "💡",
    "overview": "👁",
    "impact": "💥",
    "opportunity": "🎯",
    "challenge": "⚡",
    "solution": "🔧",
    "result": "📊",
    "objective": "🎯",
    "performance": "📈",
    "efficiency": "⚡",
    "quality": "✨",
    "default": "●",
}


def get_unicode_icon(token: str) -> str:
    """Get the best Unicode icon for a given keyword token."""
    normalized = token.lower().strip()
    if normalized in UNICODE_ICON_MAP:
        return UNICODE_ICON_MAP[normalized]
    # Fuzzy match: check if any key is a substring of the token
    for key, icon in UNICODE_ICON_MAP.items():
        if key in normalized or normalized in key:
            return icon
    return UNICODE_ICON_MAP["default"]
