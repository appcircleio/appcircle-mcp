from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("appcircle-mcp-server")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
