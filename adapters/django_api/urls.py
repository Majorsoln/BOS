"""
BOS Django adapter URL routing.
"""

from django.urls import path

from adapters.django_api import views


urlpatterns = [
    path("admin/feature-flags", views.feature_flags_list_view),
    path("admin/compliance-profiles", views.compliance_profiles_list_view),
    path("admin/document-templates", views.document_templates_list_view),
    path("docs", views.issued_documents_list_view),
    path("admin/api-keys", views.api_keys_list_view),
    path("admin/roles", views.roles_list_view),
    path("admin/actors", views.actors_list_view),
    path("admin/feature-flags/set", views.feature_flags_set_view),
    path("admin/feature-flags/clear", views.feature_flags_clear_view),
    path("admin/api-keys/create", views.api_keys_create_view),
    path("admin/api-keys/revoke", views.api_keys_revoke_view),
    path("admin/api-keys/rotate", views.api_keys_rotate_view),
    path("admin/identity/bootstrap", views.identity_bootstrap_view),
    path("admin/roles/assign", views.roles_assign_view),
    path("admin/roles/revoke", views.roles_revoke_view),
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
    path("docs/receipt/issue", views.issue_receipt_view),
    path("docs/quote/issue", views.issue_quote_view),
    path("docs/invoice/issue", views.issue_invoice_view),
]
