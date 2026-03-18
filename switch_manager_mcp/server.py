"""Main entry point: FastMCP server with Streamable HTTP, auth middleware, and status dashboard."""

from __future__ import annotations

import hmac
import html
import logging
import sys

import uvicorn
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from config import config

# Import tools so they get registered on the shared `mcp` instance.
from tools import mcp  # noqa: F401

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("switch-manager-mcp")

# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

_PUBLIC_PATHS = frozenset({"/", "/api/status"})


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token.

    Skipped entirely when MCP_AUTH_ENABLED is false, and always skipped
    for the public dashboard and status endpoint.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if not config.mcp_auth_enabled:
            return await call_next(request)

        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "Missing bearer token"}, status_code=401
            )

        provided = auth_header[7:]  # strip "Bearer "
        expected = config.mcp_auth_token or ""

        if not hmac.compare_digest(provided.encode(), expected.encode()):
            return JSONResponse(
                {"error": "Invalid token"}, status_code=403
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Dashboard & status
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Switch Manager MCP</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 4rem auto; color: #222; }}
    h1 {{ font-size: 1.4rem; }}
    .ok {{ color: #16a34a; }}
    code {{ background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 4px; }}
    .muted {{ color: #666; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>Switch Manager MCP Server</h1>
  <p class="ok">Status: running</p>
  <p>Home Assistant: <code>{ha_url}</code></p>
  <p>Auth required: <code>{auth_enabled}</code></p>
  <p class="muted">Connect an MCP client to <code>/mcp</code> (Streamable HTTP).</p>
</body>
</html>
"""


async def dashboard(request: Request) -> HTMLResponse:
    body = _DASHBOARD_HTML.format(
        ha_url=html.escape(config.ha_url),
        auth_enabled=html.escape(str(config.mcp_auth_enabled).lower()),
    )
    return HTMLResponse(body)


async def api_status(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "ha_url": config.ha_url,
            "auth_enabled": config.mcp_auth_enabled,
        }
    )


# ---------------------------------------------------------------------------
# Application assembly
# ---------------------------------------------------------------------------


def create_app():
    """Build the app by adding routes and middleware to FastMCP's http_app.

    This preserves FastMCP's lifespan (which initialises the Streamable HTTP
    task group) while adding our dashboard and auth layer.
    """
    app = mcp.http_app()

    # Prepend custom routes so they match before the MCP catch-all.
    app.routes.insert(0, Route("/", dashboard))
    app.routes.insert(1, Route("/api/status", api_status))

    # Add auth middleware.
    app.add_middleware(BearerAuthMiddleware)

    return app


app = create_app()

if __name__ == "__main__":
    logger.info(
        "Starting Switch Manager MCP on %s:%s",
        config.server_host,
        config.server_port,
    )
    uvicorn.run(
        "server:app",
        host=config.server_host,
        port=config.server_port,
        log_level=config.log_level,
    )
