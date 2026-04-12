"""Canva Connect REST: OAuth refresh + optional design thumbnail download (backend-only)."""
from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_API_BASE = "https://api.canva.com/rest/v1"


@dataclass
class CanvaClient:
    client_id: str
    client_secret: str
    refresh_token: str
    _access_token: str | None = field(default=None, repr=False)
    _expires_at: float = 0.0

    @classmethod
    def from_app_config(cls, config) -> CanvaClient | None:
        cid = (config.canva_client_id or "").strip()
        sec = (config.canva_client_secret or "").strip()
        rt = (config.canva_refresh_token or "").strip()
        if not (cid and sec and rt):
            return None
        return cls(client_id=cid, client_secret=sec, refresh_token=rt)

    def _basic_auth_header(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def get_access_token(self, force_refresh: bool = False) -> str | None:
        if (
            not force_refresh
            and self._access_token
            and time.time() < self._expires_at - 120
        ):
            return self._access_token
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    CANVA_TOKEN_URL,
                    headers={
                        "Authorization": self._basic_auth_header(),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                )
            if r.status_code != 200:
                logger.warning("Canva token refresh failed: %s %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            self._access_token = data.get("access_token")
            exp = int(data.get("expires_in", 3600))
            self._expires_at = time.time() + max(60, exp)
            if data.get("refresh_token"):
                self.refresh_token = data["refresh_token"]
            return self._access_token
        except Exception as e:
            logger.warning("Canva token request error: %s", e)
            return None

    def get_design_thumbnail_url(self, design_id: str) -> str | None:
        token = self.get_access_token()
        if not token or not design_id.strip():
            return None
        url = f"{CANVA_API_BASE}/designs/{design_id.strip()}"
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if r.status_code != 200:
                logger.warning("Canva get design failed: %s %s", r.status_code, r.text[:200])
                return None
            body: dict[str, Any] = r.json()
            design = body.get("design") or {}
            thumb = design.get("thumbnail") or {}
            u = thumb.get("url")
            return str(u) if u else None
        except Exception as e:
            logger.warning("Canva get design error: %s", e)
            return None

    def download_thumbnail(self, design_id: str, dest_dir: Path) -> Path | None:
        """Download design thumbnail PNG to dest_dir; returns local path or None."""
        img_url = self.get_design_thumbnail_url(design_id)
        if not img_url:
            return None
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / f"canva_thumb_{design_id.strip()}.png"
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                r = client.get(img_url)
            if r.status_code != 200:
                logger.warning("Canva thumbnail download failed: %s", r.status_code)
                return None
            out.write_bytes(r.content)
            return out
        except Exception as e:
            logger.warning("Canva thumbnail download error: %s", e)
            return None
