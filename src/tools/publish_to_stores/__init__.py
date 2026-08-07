"""Publish to stores tools module."""
from ...config.settings import settings
from ...core.logger import logger

# Import all publish to stores tools - decorators will auto-register them
from . import get_publish_profiles
from . import get_publish_profile_details
from . import get_app_version_metadata
from . import get_metadata_locales
from . import get_intune_metadata
from . import get_publish_metadata_lock_status
from . import get_publish_details
from . import get_publish_step_logs
from . import get_publish_flows

logger.debug(
    "Publish to stores tools imported: get_publish_profiles, get_publish_profile_details, "
    "get_app_version_metadata, get_metadata_locales, get_intune_metadata, get_publish_metadata_lock_status, "
    "get_publish_details, get_publish_step_logs, get_publish_flows"
)

# Write/action tools -- only registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled
if settings.ENABLE_WRITE_TOOLS:
    from . import start_publish
    from . import stop_publish

    logger.debug("Publish to stores write tools imported: start_publish, stop_publish")
