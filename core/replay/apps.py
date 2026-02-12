"""
BOS Replay Engine — App Configuration
=======================================
Registers replay models (checkpoints).
No startup hooks — replay is triggered explicitly.
"""

from django.apps import AppConfig


class ReplayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.replay"
    label = "replay"
    verbose_name = "BOS Replay Engine"
