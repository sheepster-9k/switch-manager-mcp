"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    ha_url: str
    ha_token: str
    mcp_auth_enabled: bool
    mcp_auth_token: str | None
    log_level: str
    server_host: str
    server_port: int

    @classmethod
    def from_environment(cls) -> Config:
        ha_token = os.environ.get("HA_TOKEN", "")
        if not ha_token:
            raise RuntimeError("HA_TOKEN environment variable is required")

        mcp_auth_token = os.environ.get("MCP_AUTH_TOKEN") or None
        mcp_auth_enabled = bool(mcp_auth_token)

        return cls(
            ha_url=os.environ.get("HA_URL", "http://supervisor/core").rstrip("/"),
            ha_token=ha_token,
            mcp_auth_enabled=mcp_auth_enabled,
            mcp_auth_token=mcp_auth_token,
            log_level=os.environ.get("LOG_LEVEL", "info").lower(),
            server_host=os.environ.get("SERVER_HOST", "0.0.0.0"),
            server_port=int(os.environ.get("PORT", "8890")),
        )


config = Config.from_environment()
