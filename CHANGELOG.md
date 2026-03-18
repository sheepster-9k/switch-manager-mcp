# Changelog

## 1.2.0

- Upgrade to FastMCP 2.14+ with native `http_app(middleware=...)` support
- Properly initialised Streamable HTTP lifespan (fixes task group error)
- Remove pydantic version pin (resolved by FastMCP 2.14+)

## 1.1.0

- Migrate from deprecated SSE transport to Streamable HTTP (`http_app()`)
- Use Python venv in Docker to isolate from system packages
- Pin pydantic<2.10 for fastmcp 2.5.1 compatibility

## 1.0.0

- Initial release
- 12 MCP tools for Switch Manager configuration management
- WebSocket client for HA Core API with auto-reconnect
- SSE transport with optional Bearer token auth
- Tools: list/get switches, list/get/source blueprints, save/delete/toggle switches
- Convenience tools: set_button_action, set_virtual_action, configure_virtual_multi_press
