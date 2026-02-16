"""
BOS Django adapter URL routing.
"""

from django.urls import path

from adapters.django_api import views


urlpatterns = [
    path("admin/feature-flags", views.feature_flags_list_view),
    path("admin/compliance-profiles", views.compliance_profiles_list_view),
    path("admin/document-templates", views.document_templates_list_view),
    path("admin/feature-flags/set", views.feature_flags_set_view),
    path("admin/feature-flags/clear", views.feature_flags_clear_view),
    path("admin/compliance-profiles/upsert", views.compliance_profiles_upsert_view),
    path(
        "admin/compliance-profiles/deactivate",
        views.compliance_profiles_deactivate_view,
    ),
    path("admin/document-templates/upsert", views.document_templates_upsert_view),
    path(
        "admin/document-templates/deactivate",
        views.document_templates_deactivate_view,
    ),
]

