#!/usr/bin/with-contenv bashio

PORT=$(bashio::config 'port' '8890')
MCP_AUTH_TOKEN=$(bashio::config 'mcp_auth_token')

export PORT
export MCP_AUTH_TOKEN
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export SERVER_HOST="0.0.0.0"

exec /opt/venv/bin/python3 /app/server.py
