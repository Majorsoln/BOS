"""
BOS Permissions Store - App Configuration
=========================================
Persistent role-to-permission grants.
"""

from django.apps import AppConfig


class CorePermissionsStoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.permissions_store"
    label = "core_permissions_store"
    verbose_name = "BOS Permissions Store"
