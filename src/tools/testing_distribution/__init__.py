"""Testing-distribution tools module."""
from ...config.settings import settings
from ...core.logger import logger

# Import all tools - decorators will auto-register them
from . import get_distribution_profiles
from . import get_distribution_profile_details
from . import get_testing_groups

logger.debug(
    "Testing Distribution tools imported: get_distribution_profiles, get_distribution_profile_details, get_testing_groups"
)

if settings.ENABLE_WRITE_TOOLS:
    from . import update_app_version_release_notes
    from . import send_app_version_to_testers

    logger.debug(
        "Testing Distribution write tools imported: update_app_version_release_notes, send_app_version_to_testers"
    )
