"""Django app config for BOS SaaS module."""
from django.apps import AppConfig


class CoreSaaSConfig(AppConfig):
    name = "core.saas"
    label = "core_saas"
    verbose_name = "BOS SaaS"
    default_auto_field = "django.db.models.BigAutoField"
