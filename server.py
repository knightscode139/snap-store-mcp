import asyncio
import subprocess
import json
from mcp.server import Server
from mcp.types import Tool, TextContent

# Create MCP server instance
server = Server("snap-store-mcp")


def parse_snap_search(output: str) -> list[dict]:
    """
    Parse snap search command output into structured data

    Input: Raw terminal output from 'snap search'
    Output: List of dictionaries with package info
    """
    lines = output.strip().split('\n')

    # Check if we have at least header + one result
    if len(lines) < 2:
        return []

    packages = []
    # Skip first line (header: Name  Version  Publisher  Notes  Summary)
    for line in lines[1:]:
        parts = line.split()
        # Ensure line has minimum required fields
        if len(parts) >= 5:
            packages.append({
                "name": parts[0],
                "version": parts[1],
                "publisher": parts[2],
                "notes": parts[3],
                "summary": " ".join(parts[4:])  # Join remaining parts as summary
            })

    return packages


def parse_snap_info(output: str) -> dict:
    """
    Parse snap info command output into structured data
    
    Input: Raw terminal output from 'snap info'
    Output: Dictionary with package details
    """
    info = {}
    lines = output.strip().split('\n')
    
    current_key = None
    current_value = []
    
    for line in lines:
        # Check if this is a new key-value pair
        if ':' in line and not line.startswith(' '):
            # Save previous key-value if exists
            if current_key:
                info[current_key] = '\n'.join(current_value)
            
            # Start new key-value
            key, value = line.split(':', 1)
            current_key = key.strip()
            current_value = [value.strip()]
        
        # This is a continuation line (indented, part of previous value)
        elif current_key and line.startswith(' '):
            current_value.append(line.strip())
    
    # Don't forget the last key-value pair
    if current_key:
        info[current_key] = '\n'.join(current_value)
    
    return info


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    Define available tools for the MCP server
    
    This tells MCP clients (like Claude) what operations are available
    """
    return [
        Tool(
            name="search_snaps",
            description="Search for snap packages in the Snap Store by name, category, or keywords. Returns matching packages even if query doesn't exactly match package name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - can be package name, category, or keywords (e.g., 'browser', 'video editor', 'python', 'game')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="snap_info",
            description="Get detailed information about a specific snap package",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Exact snap package name (e.g., 'firefox')"
                    }
                },
                "required": ["package_name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool execution requests
    
    Args:
        name: Name of the tool to execute
        arguments: Tool-specific parameters
    
    Returns:
        List of TextContent with results in JSON format
    """
    try:
        if name == "search_snaps":
            query = arguments["query"]
            
            # Execute snap search command
            result = subprocess.run(
                ["snap", "search", query],
                capture_output=True,
                text=True,
                check=True  # Raises CalledProcessError if command fails
            )
            
            # Parse raw output into structured data
            packages = parse_snap_search(result.stdout)
            
            # Convert to pretty JSON
            output = json.dumps(packages, indent=2)
            
            return [TextContent(type="text", text=output)]
        
        elif name == "snap_info":
            package_name = arguments["package_name"]
            
            # Execute snap info command
            result = subprocess.run(
                ["snap", "info", package_name],
                capture_output=True,
                text=True,
                check=True  # Raises CalledProcessError if command fails
            )
            
            # Parse raw output into structured data
            info = parse_snap_info(result.stdout)
            
            # Convert to pretty JSON
            output = json.dumps(info, indent=2)
            
            return [TextContent(type="text", text=output)]
    
    except subprocess.CalledProcessError as e:
        # Command failed (package not found, snap not installed, etc.)
        error_message = {
            "error": "Command failed",
            "command": " ".join(e.cmd),
            "stderr": e.stderr.strip() if e.stderr else "No error details available",
            "suggestion": "Check if the package name is correct. Try using 'search_snaps' first."
        }
        return [TextContent(type="text", text=json.dumps(error_message, indent=2))]
    
    except Exception as e:
        # Unexpected error
        error_message = {
            "error": "Unexpected error",
            "details": str(e),
            "suggestion": "Please report this issue on GitHub"
        }
        return [TextContent(type="text", text=json.dumps(error_message, indent=2))]

async def main():
    """
    Main entry point - start MCP server with stdio transport
    
    stdio: Server communicates via standard input/output (required by MCP protocol)
    """
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
