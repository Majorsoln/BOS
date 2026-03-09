"""
BOS Django adapter URL routing.
"""

from django.urls import path

from adapters.django_api import views


urlpatterns = [
    path("admin/business", views.business_profile_view),
    path("admin/branches", views.branches_list_view),
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
    path("admin/actors/deactivate", views.actors_deactivate_view),
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
    # Tax rule configuration
    path("admin/tax-rules", views.tax_rules_list_view),
    path("admin/tax-rules/set", views.tax_rules_set_view),
    # Business profile update
    path("admin/business/update", views.business_update_view),
    # Custom role creation
    path("admin/roles/create", views.roles_create_view),
    # Customer profile CRUD
    path("admin/customers", views.customers_list_view),
    path("admin/customers/create", views.customers_create_view),
    path("admin/customers/update", views.customers_update_view),
    path("docs/receipt/issue", views.issue_receipt_view),
    path("docs/quote/issue", views.issue_quote_view),
    path("docs/invoice/issue", views.issue_invoice_view),
    # Generic document issue endpoint — handles all 25 document types
    # Must come AFTER the specific paths above to avoid shadowing them
    path("docs/<str:doc_type>/issue", views.issue_document_type_view),
    # Phase 3: render & verification
    path("docs/<uuid:document_id>/render-plan", views.document_render_plan_view),
    path("docs/<uuid:document_id>/render-html", views.document_render_html_view),
    path("docs/<uuid:document_id>/render-pdf", views.document_render_pdf_view),
    path("docs/<uuid:document_id>/verify", views.document_verify_view),
    # Data Migration ("Hamisha Data") endpoints
    path("admin/migration/create-job", views.migration_create_job_view),
    path("admin/migration/upload", views.migration_upload_view),
    path("admin/migration/complete", views.migration_complete_view),
    path("admin/migration/cancel", views.migration_cancel_view),
    path("admin/migration/jobs", views.migration_jobs_list_view),
    path("admin/migration/mappings", views.migration_mappings_view),
    # SaaS — Engine Combos & Pricing
    path("saas/engines", views.saas_engines_list_view),
    path("saas/engines/register", views.saas_register_engine_view),
    path("saas/combos", views.saas_combos_list_view),
    path("saas/combos/define", views.saas_define_combo_view),
    path("saas/combos/update", views.saas_update_combo_view),
    path("saas/combos/deactivate", views.saas_deactivate_combo_view),
    path("saas/combos/set-rate", views.saas_set_combo_rate_view),
    path("saas/pricing", views.saas_pricing_catalog_view),
    # SaaS — Trial Policy & Agreements
    path("saas/trial-policy", views.saas_trial_policy_view),
    path("saas/trial-policy/set", views.saas_set_trial_policy_view),
    path("saas/trials/create", views.saas_create_trial_view),
    path("saas/trials/extend", views.saas_extend_trial_view),
    path("saas/trials/convert", views.saas_convert_trial_view),
    path("saas/trials/agreement", views.saas_trial_agreement_view),
    # SaaS — Rate Governance
    path("saas/rates/publish-change", views.saas_publish_rate_change_view),
    path("saas/rates/effective", views.saas_effective_rate_view),
    # SaaS — Promotions
    path("saas/promos", views.saas_promos_list_view),
    path("saas/promos/create", views.saas_create_promo_view),
    path("saas/promos/redeem", views.saas_redeem_promo_view),
    # SaaS — Referrals ("Alika Rafiki")
    path("saas/referrals/set-policy", views.saas_set_referral_policy_view),
    path("saas/referrals/generate-code", views.saas_generate_referral_code_view),
    path("saas/referrals/submit", views.saas_submit_referral_view),
    path("saas/referrals/qualify", views.saas_qualify_referral_view),
    # SaaS — Resellers ("Wakala wa BOS")
    path("saas/resellers", views.saas_resellers_list_view),
    path("saas/resellers/register", views.saas_register_reseller_view),
    path("saas/resellers/link-tenant", views.saas_link_tenant_view),
    path("saas/resellers/accrue-commission", views.saas_accrue_commission_view),
    path("saas/resellers/request-payout", views.saas_request_payout_view),
    # SaaS — Subscriptions
    path("saas/subscriptions", views.saas_subscription_view),
    path("saas/subscriptions/start-trial", views.saas_start_trial_sub_view),
    path("saas/subscriptions/activate", views.saas_activate_sub_view),
    path("saas/subscriptions/cancel", views.saas_cancel_sub_view),
    path("saas/subscriptions/change-combo", views.saas_change_combo_view),
]
