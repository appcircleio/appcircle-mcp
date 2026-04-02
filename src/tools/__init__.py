"""Tools module - loads toolset subpackages unless excluded in settings."""

import importlib

from ..config.settings import TOOLSETS, settings
from ..core.logger import logger

excluded = getattr(settings, "EXCLUDED_TOOLSETS", set())
for name in sorted(TOOLSETS):
    if name not in excluded:
        importlib.import_module(f".{name}", package=__name__)
        logger.debug("Toolset loaded: %s", name)
    else:
        logger.debug("Toolset excluded: %s", name)

logger.debug("Tools module imported - tools registered for non-excluded toolsets")