"""Build tools module."""
from ...config.settings import settings
from ...core.logger import logger

# Import all build tools - decorators will auto-register them
from . import get_build_profiles
from . import get_build_profile_details
from . import get_build_configuration_details
from . import get_build_profile_workflows
from . import get_workflow_detail
from . import get_commits_by_branch
from . import get_commit_details
from . import get_last_commit
from . import get_build_status
from . import get_build_logs
from . import get_variable_groups

logger.debug(
    "Build tools imported: get_build_profiles, get_build_profile_details, get_build_configuration_details, get_build_profile_workflows, get_workflow_detail, get_commits_by_branch, get_commit_details, get_last_commit, get_build_status, get_build_logs, get_variable_groups"
)

# Write/action tools -- only registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled
if settings.ENABLE_WRITE_TOOLS:
    from . import trigger_build
    from . import cancel_build

    logger.debug("Build write tools imported: trigger_build, cancel_build")