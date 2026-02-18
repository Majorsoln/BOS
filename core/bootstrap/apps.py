"""
BOS Bootstrap — App Configuration
===================================
Triggers system self-check when Django finishes loading.

Rules:
- Runs once via ready()
- Skips during migrations (tables may not exist yet)
- Skips during management commands that don't need full boot
- If self-check fails → SystemBootstrapError prevents startup
"""

import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger("bos.bootstrap")

# Commands that should NOT trigger bootstrap checks
# (tables may not exist, system is being set up)
SKIP_COMMANDS = {
    "migrate",
    "makemigrations",
    "showmigrations",
    "sqlmigrate",
    "flush",
    "createsuperuser",
    "shell",
    "dbshell",
    "inspectdb",
    "test",
    "collectstatic",
    "check",
}


def _is_management_command_skip():
    """Check if current command should skip bootstrap checks."""
    if len(sys.argv) >= 2:
        return sys.argv[1] in SKIP_COMMANDS
    return False


def _is_pytest_context() -> bool:
    return (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
    )


class BootstrapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.bootstrap"
    label = "bootstrap"
    verbose_name = "BOS Bootstrap"

    def ready(self):
        if _is_management_command_skip() or _is_pytest_context():
            logger.info(
                "Bootstrap self-check skipped for management/test context."
            )
            return

        from core.bootstrap.self_check import run_bootstrap_checks
        run_bootstrap_checks()
