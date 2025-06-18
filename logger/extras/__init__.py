"""Extras utilities for the logger package."""

from .dependency import DependencyManager, logger_log_environment
from .network import (
    NetworkMonitor,
    logger_check_connectivity,
    logger_get_network_metrics,
    _setup_dependencies_and_network,
)
from .progress import LoggerProgressBar, logger_progress, format_block, combine_blocks
from .printing import logger_capture_prints
from .helpers import _init_colorama, _setup_directories, _get_log_filename, _attach_screenshot
from .metrics import MetricsTracker, logger_reset_metrics, logger_report_metrics, _setup_metrics
from .monitoring import (
    SystemMonitor,
    logger_log_system_status,
    logger_memory_snapshot,
    logger_check_memory_leak,
    _setup_monitoring,
)
from .utils.sleep import logger_sleep
from .utils.timer import Timer, logger_timer
from .logger_lifecycle import logger_log_start, logger_log_end, _setup_lifecycle
from .base_funcs import *  # noqa: F401,F403
