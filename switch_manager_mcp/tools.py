"""MCP tool definitions for Switch Manager configuration."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ha_client import client

mcp = FastMCP("switch-manager-mcp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Convert a config from the WS GET response into SAVE-compatible format.

    The GET response includes the blueprint as a nested object; the SAVE
    endpoint expects just the blueprint ID string.
    """
    blueprint = config.get("blueprint", "")
    if isinstance(blueprint, dict):
        blueprint = blueprint.get("id", "")

    return {
        "id": config.get("id"),
        "name": config.get("name"),
        "enabled": config.get("enabled", True),
        "blueprint": blueprint,
        "identifier": config.get("identifier"),
        "variables": config.get("variables"),
        "device_id": config.get("device_id"),
        "primary_entity_id": config.get("primary_entity_id"),
        "property_entity_ids": config.get("property_entity_ids", []),
        "metadata": config.get("metadata"),
        "virtual_multi_press": config.get("virtual_multi_press", {}),
        "buttons": [_normalize_button(b) for b in config.get("buttons", [])],
    }


def _normalize_button(button: dict[str, Any]) -> dict[str, Any]:
    return {
        "actions": [
            {"mode": a.get("mode", "single"), "sequence": a.get("sequence", [])}
            for a in button.get("actions", [])
        ],
        "virtual_actions": [
            {
                "title": va.get("title", ""),
                "press_count": va.get("press_count", 1),
                "mode": va.get("mode", "single"),
                "sequence": va.get("sequence", []),
            }
            for va in button.get("virtual_actions", [])
        ],
    }


# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_blueprints() -> list[dict[str, Any]]:
    """List all available Switch Manager blueprints.

    Returns a list of blueprints with id, name, service type, event_type,
    and button definitions.
    """
    result = await client.call("switch_manager/blueprints")
    return result.get("blueprints", [])


@mcp.tool()
async def get_blueprint(blueprint_id: str) -> dict[str, Any]:
    """Get full details for a single blueprint.

    Args:
        blueprint_id: The blueprint identifier string (e.g.
            'custom-zigbee2mqtt-philips-hue-twilight').
    """
    result = await client.call("switch_manager/blueprints", blueprint_id=blueprint_id)
    return result.get("blueprint", {})


@mcp.tool()
async def get_blueprint_source(blueprint_id: str) -> dict[str, Any]:
    """Get the raw YAML definition of a blueprint.

    Args:
        blueprint_id: The blueprint identifier string.
    """
    result = await client.call(
        "switch_manager/blueprints/source", blueprint_id=blueprint_id
    )
    return result.get("definition", {})


# ---------------------------------------------------------------------------
# Switches (configs)
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_switches() -> list[dict[str, Any]]:
    """List all configured switches.

    Returns each switch with its id, name, blueprint, identifier, enabled
    state, buttons, and virtual_multi_press settings.
    """
    result = await client.call("switch_manager/configs")
    return result.get("configs", [])


@mcp.tool()
async def get_switch(config_id: str) -> dict[str, Any]:
    """Get full details for a single switch configuration.

    Args:
        config_id: The switch config ID (string or numeric).
    """
    result = await client.call("switch_manager/configs", config_id=config_id)
    return result.get("config", {})


@mcp.tool()
async def save_switch(config: dict[str, Any]) -> dict[str, Any]:
    """Create or update a switch configuration (full replace).

    Pass the complete config dict matching the Switch Manager schema.
    Omit 'id' (or set to null) to create a new switch; include 'id' to update.

    Required fields: name, blueprint (ID string), identifier, buttons.
    Each button needs 'actions' (list of {mode, sequence}) and optionally
    'virtual_actions' (list of {title, press_count, mode, sequence}).

    Args:
        config: Full switch configuration dict.
    """
    result = await client.call("switch_manager/config/save", config=config)
    return result


@mcp.tool()
async def delete_switch(config_id: str) -> dict[str, Any]:
    """Delete a switch configuration.

    Args:
        config_id: The switch config ID to delete.
    """
    return await client.call("switch_manager/config/delete", config_id=config_id)


@mcp.tool()
async def toggle_switch(config_id: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable a switch configuration.

    Args:
        config_id: The switch config ID.
        enabled: True to enable, False to disable.
    """
    return await client.call(
        "switch_manager/config/enabled", config_id=config_id, enabled=enabled
    )


@mcp.tool()
async def list_switches_by_blueprint(blueprint_id: str) -> list[dict[str, Any]]:
    """List all switches that use a specific blueprint (useful for copying configs).

    Args:
        blueprint_id: The blueprint ID to filter by.
    """
    result = await client.call(
        "switch_manager/copy_from_list", blueprint_id=blueprint_id
    )
    return result.get("switches", [])


# ---------------------------------------------------------------------------
# Convenience: modify individual button actions
# ---------------------------------------------------------------------------


@mcp.tool()
async def set_button_action(
    config_id: str,
    button_index: int,
    action_index: int,
    sequence: list[dict[str, Any]],
    mode: str = "single",
) -> dict[str, Any]:
    """Set the action sequence for one button action on an existing switch.

    This does a get-modify-save internally so only the targeted action changes.

    Args:
        config_id: The switch config ID.
        button_index: Zero-based button index.
        action_index: Zero-based action index within the button.
        sequence: HA action sequence (list of service call dicts).
        mode: Script mode — 'single', 'restart', 'queued', or 'parallel'.
    """
    raw = await client.call("switch_manager/configs", config_id=config_id)
    cfg = _normalize_config(raw.get("config", {}))

    buttons = cfg["buttons"]
    if button_index < 0 or button_index >= len(buttons):
        raise ValueError(f"button_index {button_index} out of range (0–{len(buttons) - 1})")
    actions = buttons[button_index]["actions"]
    if action_index < 0 or action_index >= len(actions):
        raise ValueError(f"action_index {action_index} out of range (0–{len(actions) - 1})")

    actions[action_index] = {"mode": mode, "sequence": sequence}

    return await client.call("switch_manager/config/save", config=cfg)


@mcp.tool()
async def set_virtual_action(
    config_id: str,
    button_index: int,
    press_count: int,
    sequence: list[dict[str, Any]],
    title: str = "",
    mode: str = "single",
) -> dict[str, Any]:
    """Add or update a virtual (multi-press) action on a button.

    If a virtual action with the same press_count already exists on this
    button, it is updated; otherwise a new one is appended.

    Args:
        config_id: The switch config ID.
        button_index: Zero-based button index.
        press_count: Number of presses (2 = double press, 3 = triple, etc.).
        sequence: HA action sequence.
        title: Human-readable action title (defaults to 'press Nx').
        mode: Script mode.
    """
    raw = await client.call("switch_manager/configs", config_id=config_id)
    cfg = _normalize_config(raw.get("config", {}))

    buttons = cfg["buttons"]
    if button_index < 0 or button_index >= len(buttons):
        raise ValueError(f"button_index {button_index} out of range (0–{len(buttons) - 1})")

    if not title:
        title = f"press {press_count}x"

    btn = buttons[button_index]
    virtual_actions = btn.get("virtual_actions", [])

    # Update existing or append
    found = False
    for va in virtual_actions:
        if va["press_count"] == press_count:
            va["title"] = title
            va["sequence"] = sequence
            va["mode"] = mode
            found = True
            break
    if not found:
        virtual_actions.append({
            "title": title,
            "press_count": press_count,
            "mode": mode,
            "sequence": sequence,
        })

    btn["virtual_actions"] = virtual_actions
    return await client.call("switch_manager/config/save", config=cfg)


@mcp.tool()
async def configure_virtual_multi_press(
    config_id: str,
    enabled: bool = True,
    press_window_ms: int = 450,
    max_presses: int = 3,
) -> dict[str, Any]:
    """Configure the virtual multi-press settings on a switch.

    Args:
        config_id: The switch config ID.
        enabled: Whether virtual multi-press is active.
        press_window_ms: Window in ms to accumulate presses (150–3000).
        max_presses: Maximum press count to track (2–10).
    """
    raw = await client.call("switch_manager/configs", config_id=config_id)
    cfg = _normalize_config(raw.get("config", {}))

    cfg["virtual_multi_press"] = {
        "enabled": enabled,
        "press_window_ms": press_window_ms,
        "max_presses": max_presses,
    }

    return await client.call("switch_manager/config/save", config=cfg)
