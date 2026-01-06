# Snap Store MCP Server

MCP server for Snap Store - search and get snap package info.

## Install
```bash
git clone https://github.com/knightscode139/snap-store-mcp.git
cd snap-store-mcp
uv sync
```

## Test
```bash
npx @modelcontextprotocol/inspector uv run server.py
```

## Tools

**search_snaps** - Search packages
```bash
Input: {"query": "browser"}
```

**snap_info** - Package details
```bash
Input: {"package_name": "firefox"}
```