"""
BOS Auth - App Configuration
============================
Persistent API key credential storage and lookup.
"""

from django.apps import AppConfig


class CoreAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.auth"
    label = "core_auth"
    verbose_name = "BOS Auth"
