# Switch Manager MCP

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server for AI-assisted management of [Home Assistant Switch Manager](https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager) button configurations. Runs as a Home Assistant add-on and exposes 12 tools over Streamable HTTP transport.

## What it does

Switch Manager MCP lets an LLM (Claude, GPT, etc.) read and write your Switch Manager configurations through a structured API instead of editing raw JSON in `.storage/switch_manager`. This means you can describe what you want a button to do in natural language and have the AI program it for you.

**Example prompts:**

- *"Set the left lamp's top button to toggle `light.left_lamp_front` and `light.left_lamp_back`"*
- *"Add a double-press on button 0 to toggle all living room lamps"*
- *"Enable virtual multi-press on the bedroom lamp switches with a 450ms window"*
- *"Show me all switches using the Hue Twilight blueprint"*

## Installation

### Add the repository

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**
2. Click the **three-dot menu** (top right) > **Repositories**
3. Add: `https://github.com/sheepster-9k/switch-manager-mcp`
4. Click **Close**, then find **Switch Manager MCP** in the store and click **Install**

### Configure

The add-on has two configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `port` | `8890` | Port the MCP server listens on |
| `mcp_auth_token` | *(empty)* | Optional Bearer token for authentication. When set, all MCP requests must include `Authorization: Bearer <token>`. Leave empty to disable auth. |

### Start

Click **Start**. The server will connect to Home Assistant Core via the internal Supervisor WebSocket API and begin accepting MCP connections.

## Connecting an MCP client

### Claude Code

Add to your MCP config (`.claude/settings.json` or project-level):

```json
{
  "mcpServers": {
    "switch-manager": {
      "type": "url",
      "url": "http://<HA_IP>:8890/mcp"
    }
  }
}
```

Replace `<HA_IP>` with your Home Assistant IP (e.g. `192.168.1.100`).

If you set an auth token, add the header:

```json
{
  "mcpServers": {
    "switch-manager": {
      "type": "url",
      "url": "http://<HA_IP>:8890/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Other MCP clients

Point any MCP-compatible client at `http://<HA_IP>:8890/mcp` using Streamable HTTP transport.

## Tools

### Blueprints

| Tool | Description |
|------|-------------|
| `list_blueprints` | List all available blueprints (id, name, service type, buttons) |
| `get_blueprint` | Get full details for a single blueprint by ID |
| `get_blueprint_source` | Get the raw YAML definition of a blueprint |

### Switch configurations

| Tool | Description |
|------|-------------|
| `list_switches` | List all configured switches with their settings |
| `get_switch` | Get full details for a single switch by config ID |
| `save_switch` | Create or update a switch config (full replace). Omit `id` to create new |
| `delete_switch` | Delete a switch configuration |
| `toggle_switch` | Enable or disable a switch without changing its config |
| `list_switches_by_blueprint` | List all switches using a specific blueprint |

### Convenience tools

These do a get-modify-save internally so you only specify what changes:

| Tool | Description |
|------|-------------|
| `set_button_action` | Set the action sequence for a specific button/action by index |
| `set_virtual_action` | Add or update a virtual (multi-press) action on a button |
| `configure_virtual_multi_press` | Configure virtual multi-press settings (enable, window, max presses) |

## Architecture

```
MCP Client (Claude Code, etc.)
    |
    | Streamable HTTP (:8890/mcp)
    v
+---------------------------+
|  Switch Manager MCP       |
|  (FastMCP + Starlette)    |
|  - Auth middleware         |
|  - 12 MCP tools           |
+---------------------------+
    |
    | WebSocket (ws://supervisor/core/api/websocket)
    | Authenticated via SUPERVISOR_TOKEN
    v
+---------------------------+
|  Home Assistant Core      |
|  Switch Manager WS API    |
|  - switch_manager/configs |
|  - switch_manager/config/ |
|    save, delete, enabled  |
|  - switch_manager/        |
|    blueprints, copy_from  |
+---------------------------+
```

The add-on authenticates to HA Core using the `SUPERVISOR_TOKEN` provided automatically by the Supervisor. No manual token configuration is needed for the HA connection.

## Switch config schema

When using `save_switch`, provide a config dict with this structure:

```json
{
  "id": null,
  "name": "My Switch",
  "enabled": true,
  "blueprint": "custom-zigbee2mqtt-philips-hue-twilight",
  "identifier": "zigbee2mqtt/0x001788010xxx/action",
  "buttons": [
    {
      "actions": [
        {
          "mode": "single",
          "sequence": [
            {
              "action": "light.toggle",
              "target": { "entity_id": "light.my_lamp" }
            }
          ]
        }
      ],
      "virtual_actions": [
        {
          "title": "double press",
          "press_count": 2,
          "mode": "single",
          "sequence": [
            {
              "action": "light.toggle",
              "target": { "entity_id": "light.all_lamps" }
            }
          ]
        }
      ]
    }
  ],
  "virtual_multi_press": {
    "enabled": true,
    "press_window_ms": 450,
    "max_presses": 2
  }
}
```

- Set `id` to `null` to create a new switch, or include the existing ID to update
- `blueprint` must be the blueprint ID string (not the full object)
- Each button's `actions` array must match the blueprint's action count
- `virtual_actions` and `virtual_multi_press` are optional

## Endpoints

| Path | Description |
|------|-------------|
| `/` | Status dashboard (HTML) |
| `/api/status` | JSON health check |
| `/mcp` | MCP Streamable HTTP endpoint |

## Requirements

- Home Assistant with [Switch Manager](https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager) installed
- The add-on requires `homeassistant_api` and `hassio_api` access (configured automatically)

## License

MIT
