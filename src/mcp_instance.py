"""MCP server instance - shared across the application."""
from mcp.server.fastmcp import FastMCP
from mcp.types import Icon

from . import __version__

# Initialize FastMCP
mcp = FastMCP(
    "Appcircle MCP", 
    stateless_http=True, 
    json_response=True,
    website_url="https://appcircle.io",
    icons=[
        Icon(
            src="./appcircle-mcp.png",
            mimeType="image/png",
            sizes=["48x48"]
        )
    ]
)

# serverInfo.version in the initialize response
mcp._mcp_server.version = __version__
