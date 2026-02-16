"""
BOS Root URL Configuration
Thin adapter routes only.
"""

from django.urls import include, path


urlpatterns = [
    path("v1/", include("adapters.django_api.urls")),
]

