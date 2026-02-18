"""
BOS Identity Store - App Configuration
======================================
Persistent identity primitives: business, branch, actor, role, assignment.
"""

from django.apps import AppConfig


class CoreIdentityStoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.identity_store"
    label = "core_identity_store"
    verbose_name = "BOS Identity Store"
