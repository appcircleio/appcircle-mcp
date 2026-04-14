"""MCP server instance - shared across the application."""
from mcp.server.fastmcp import FastMCP
from mcp.types import Icon

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