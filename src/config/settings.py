from typing import Iterable, Optional

# Canonical toolset IDs; used for validation and conditional loading
TOOLSETS = frozenset({
    "build_module",
    "signing_identities",
    "testing_distribution",
    "publish_to_stores",
    "enterprise_app_store",
    "report",
})


class Settings:
    APPCIRCLE_API_URL: str = "https://api.appcircle.io" # Default, can be overridden
    APPCIRCLE_ACCESS_TOKEN: Optional[str] = None

     # Server Name
    MCP_SERVER_NAME: str = "Appcircle MCP"

    # API Settings
    REQUEST_TIMEOUT: int = 300 # in seconds
    MAX_RETRIES: int = 3

    # Toolsets to exclude from registration (set via set_excluded_toolsets)
    EXCLUDED_TOOLSETS: set = set()

    @classmethod
    def set_access_token(cls, token: str) -> None:
        """Set the access token from MCP configuration."""
        cls.APPCIRCLE_ACCESS_TOKEN = token

    @classmethod
    def set_api_url(cls, url: str) -> None:
        """Set the API URL from MCP configuration."""
        cls.APPCIRCLE_API_URL = url.rstrip('/')  # Remove trailing slash if present

    @classmethod
    def configure(cls, access_token: str, api_url: str, ) -> None:
        """
        Configure the settings at runtime.
        
        Args:
            access_token: Appcircle API access token
            api_url: Optional custom API URL for self-hosted environments (defaults to https://api.appcircle.io)
        """
        cls.set_access_token(access_token)
        if api_url:
            cls.set_api_url(api_url)

    @classmethod
    def validate(cls) -> None:
        """Validate that all required settings are set."""
        if not cls.APPCIRCLE_ACCESS_TOKEN:
            raise ValueError(
                "APPCIRCLE_ACCESS_TOKEN is required. "
                "Please configure it in your MCP client settings."
            )

    @classmethod
    def set_excluded_toolsets(cls, names: Iterable[str]) -> None:
        """
        Set which toolsets to exclude from registration.
        Names are validated against TOOLSETS; invalid names raise ValueError.
        """
        normalized = {n.strip() for n in names if n and n.strip()}
        invalid = normalized - TOOLSETS
        if invalid:
            raise ValueError(
                f"Invalid toolset(s): {sorted(invalid)}. "
                f"Valid toolsets: {sorted(TOOLSETS)}."
            )
        cls.EXCLUDED_TOOLSETS = normalized

settings = Settings()