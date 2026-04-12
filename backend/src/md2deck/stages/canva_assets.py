"""Canva Connect API integration for premium graphics and design assets.

Uses OAuth2 Authorization Code flow. For automated server-side usage, we
pre-authorize and cache the access token, then use refresh tokens.

Canva API capabilities used:
  - Asset search/listing for premium icons and illustrations
  - Design creation for generating custom slide graphics
  - Export API for downloading rendered assets as PNG

The Canva API requires user-delegated OAuth. For our use case, we implement
a simplified flow that works with client credentials + pre-authorized tokens.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CANVA_AUTH_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_API_BASE = "https://api.canva.com/rest/v1"

# Token cache to avoid re-auth in the same session
_token_cache: dict[str, dict[str, Any]] = {}


@dataclass(slots=True)
class CanvaConfig:
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expires: float = 0.0


@dataclass(slots=True)
class CanvaAsset:
    asset_id: str
    name: str
    asset_type: str
    thumbnail_url: str
    local_path: Path | None = None


def get_auth_header(config: CanvaConfig) -> dict[str, str]:
    """Build authorization header for Canva API requests."""
    if config.access_token:
        return {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }
    return {}


def exchange_token(config: CanvaConfig, auth_code: str, redirect_uri: str, code_verifier: str) -> dict[str, Any]:
    """Exchange authorization code for access token using PKCE flow."""
    try:
        # Basic auth header
        credentials = base64.b64encode(
            f"{config.client_id}:{config.client_secret}".encode()
        ).decode()

        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                CANVA_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            if response.status_code != 200:
                logger.error(f"Canva token exchange failed: {response.status_code} {response.text}")
                return {}
            token_data = response.json()
            config.access_token = token_data.get("access_token", "")
            config.refresh_token = token_data.get("refresh_token", "")
            config.token_expires = time.time() + token_data.get("expires_in", 3600)
            return token_data
    except Exception as e:
        logger.error(f"Canva token exchange error: {e}")
        return {}


def refresh_access_token(config: CanvaConfig) -> bool:
    """Refresh an expired access token."""
    if not config.refresh_token:
        return False
    try:
        credentials = base64.b64encode(
            f"{config.client_id}:{config.client_secret}".encode()
        ).decode()

        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                CANVA_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": config.refresh_token,
                },
            )
            if response.status_code != 200:
                logger.error(f"Canva token refresh failed: {response.status_code}")
                return False
            token_data = response.json()
            config.access_token = token_data.get("access_token", "")
            config.refresh_token = token_data.get("refresh_token", config.refresh_token)
            config.token_expires = time.time() + token_data.get("expires_in", 3600)
            return True
    except Exception as e:
        logger.error(f"Canva token refresh error: {e}")
        return False


def ensure_valid_token(config: CanvaConfig) -> bool:
    """Ensure we have a valid, non-expired access token."""
    if not config.access_token:
        return False
    if time.time() >= config.token_expires - 60:
        return refresh_access_token(config)
    return True


# ─── Asset Operations ──────────────────────────────────────────────


def list_assets(config: CanvaConfig, asset_type: str = "image") -> list[dict[str, Any]]:
    """List available assets from the user's Canva content library."""
    if not ensure_valid_token(config):
        return []
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{CANVA_API_BASE}/assets",
                headers=get_auth_header(config),
            )
            if response.status_code != 200:
                logger.warning(f"Canva list assets failed: {response.status_code}")
                return []
            data = response.json()
            items = data.get("items", [])
            return [item for item in items if item.get("type", "") == asset_type]
    except Exception as e:
        logger.warning(f"Canva list assets error: {e}")
        return []


def upload_asset(config: CanvaConfig, file_path: Path, name: str = "") -> str | None:
    """Upload a local asset to Canva's content library. Returns asset ID."""
    if not ensure_valid_token(config):
        return None
    if not file_path.exists():
        return None

    asset_name = name or file_path.stem
    try:
        with httpx.Client(timeout=30.0) as client:
            # Start asset upload job
            response = client.post(
                f"{CANVA_API_BASE}/asset-uploads",
                headers={
                    "Authorization": f"Bearer {config.access_token}",
                    "Content-Type": "application/octet-stream",
                    "Asset-Upload-Metadata": f'{{"name_base64": "{base64.b64encode(asset_name.encode()).decode()}"}}',
                },
                content=file_path.read_bytes(),
            )
            if response.status_code not in (200, 201):
                logger.warning(f"Canva asset upload failed: {response.status_code}")
                return None
            job_data = response.json()
            job_id = job_data.get("job", {}).get("id")
            if not job_id:
                return None

            # Poll for completion
            for _ in range(20):
                time.sleep(1.5)
                status_resp = client.get(
                    f"{CANVA_API_BASE}/asset-uploads/{job_id}",
                    headers=get_auth_header(config),
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    job_status = status_data.get("job", {}).get("status")
                    if job_status == "success":
                        return status_data.get("job", {}).get("asset", {}).get("id")
                    if job_status == "failed":
                        logger.warning("Canva asset upload job failed")
                        return None
            return None
    except Exception as e:
        logger.warning(f"Canva asset upload error: {e}")
        return None


# ─── Design Operations ─────────────────────────────────────────────


def create_design(
    config: CanvaConfig,
    title: str,
    design_type: str = "whiteboard",
    width: int = 1920,
    height: int = 1080,
) -> str | None:
    """Create a new Canva design. Returns design ID."""
    if not ensure_valid_token(config):
        return None
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{CANVA_API_BASE}/designs",
                headers=get_auth_header(config),
                json={
                    "design_type": {"type": design_type},
                    "title": title,
                },
            )
            if response.status_code not in (200, 201):
                logger.warning(f"Canva create design failed: {response.status_code}")
                return None
            data = response.json()
            return data.get("design", {}).get("id")
    except Exception as e:
        logger.warning(f"Canva create design error: {e}")
        return None


def export_design(
    config: CanvaConfig,
    design_id: str,
    format_type: str = "png",
    cache_dir: Path = Path("."),
) -> Path | None:
    """Export a Canva design as an image. Returns local file path."""
    if not ensure_valid_token(config):
        return None
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=30.0) as client:
            # Start export job
            response = client.post(
                f"{CANVA_API_BASE}/exports",
                headers=get_auth_header(config),
                json={
                    "design_id": design_id,
                    "format": {"type": format_type},
                },
            )
            if response.status_code not in (200, 201):
                logger.warning(f"Canva export failed: {response.status_code}")
                return None
            job_data = response.json()
            job_id = job_data.get("job", {}).get("id")
            if not job_id:
                return None

            # Poll for export completion (up to 30 seconds)
            for _ in range(20):
                time.sleep(1.5)
                status_resp = client.get(
                    f"{CANVA_API_BASE}/exports/{job_id}",
                    headers=get_auth_header(config),
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    job_status = status_data.get("job", {}).get("status")
                    if job_status == "success":
                        urls = status_data.get("job", {}).get("urls", [])
                        if urls:
                            # Download the exported image
                            img_resp = client.get(urls[0])
                            if img_resp.status_code == 200:
                                local_path = cache_dir / f"canva_{design_id}.{format_type}"
                                local_path.write_bytes(img_resp.content)
                                logger.info(f"Exported Canva design to {local_path}")
                                return local_path
                    if job_status == "failed":
                        logger.warning("Canva export job failed")
                        return None
            return None
    except Exception as e:
        logger.warning(f"Canva export error: {e}")
        return None


# ─── Premium Graphics Search ──────────────────────────────────────


def search_canva_graphics(
    config: CanvaConfig,
    query: str,
    cache_dir: Path,
    limit: int = 3,
) -> list[Path]:
    """Search Canva for premium graphics/illustrations and export them as PNGs.

    Since Canva Connect API doesn't have a direct 'search content library' endpoint,
    we create designs with specific content themes and export them. For an
    existing library with uploaded graphics, we list and filter assets.
    """
    if not ensure_valid_token(config):
        logger.info("Canva token not valid, skipping premium graphics search.")
        return []

    paths: list[Path] = []

    # Try listing existing assets that match the query
    assets = list_assets(config, asset_type="image")
    matching = [a for a in assets if query.lower() in (a.get("name", "") or "").lower()][:limit]

    for asset in matching:
        thumbnail_url = asset.get("thumbnail", {}).get("url")
        if thumbnail_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(thumbnail_url, headers=get_auth_header(config))
                    if resp.status_code == 200:
                        local = cache_dir / f"canva_asset_{asset['id']}.png"
                        local.write_bytes(resp.content)
                        paths.append(local)
            except Exception:
                continue

    return paths


# ─── PKCE Helpers ──────────────────────────────────────────────────


def generate_pkce_verifier() -> str:
    """Generate a PKCE code_verifier for the OAuth flow."""
    return secrets.token_urlsafe(64)[:128]


def generate_pkce_challenge(verifier: str) -> str:
    """Generate a PKCE code_challenge from the code_verifier (S256 method)."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def build_authorization_url(config: CanvaConfig, redirect_uri: str, scopes: list[str]) -> tuple[str, str]:
    """Build the Canva OAuth authorization URL. Returns (url, code_verifier)."""
    verifier = generate_pkce_verifier()
    challenge = generate_pkce_challenge(verifier)
    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{CANVA_AUTH_URL}?{query}", verifier
