"""
SaaS Persistence Store — DB-backed store that syncs between Django ORM and in-memory projections.

Pattern:
    LOAD (startup):  DB rows → projection.apply(event_type, payload) → in-memory state rebuilt
    SAVE (mutation):  service calls save_*() → Django ORM update_or_create → DB persisted

All Django model imports are lazy (inside methods) to avoid circular imports at module level.
"""
from __future__ import annotations


class SaaSPersistenceStore:
    """
    Bridge between in-memory SaaS projections and Django ORM persistence.

    Load: DB -> in-memory projection (on startup)
    Save: in-memory projection -> DB (after each mutation)
    """

    # =================================================================
    # Plans — engines, combos, rates
    # =================================================================

    @staticmethod
    def load_plan_projection(projection: "PlanProjection") -> None:
        """Load engines, combos, rates from DB into the projection."""
        from core.saas.models import SaaSEngine, SaaSCombo, SaaSComboRate

        # Load engines
        for row in SaaSEngine.objects.all():
            projection.apply("saas.engine.registered.v1", {
                "engine_key": row.engine_key,
                "display_name": row.display_name,
                "category": row.category,
                "description": row.description,
            })

        # Load combos
        for row in SaaSCombo.objects.all():
            projection.apply("saas.combo.defined.v1", {
                "combo_id": str(row.combo_id),
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
                "business_model": row.business_model,
                "paid_engines": row.paid_engines,
                "max_branches": row.max_branches,
                "max_users": row.max_users,
                "max_api_calls_per_month": row.max_api_calls_per_month,
                "max_documents_per_month": row.max_documents_per_month,
                "sort_order": row.sort_order,
            })
            if row.status == "DEACTIVATED":
                projection.apply("saas.combo.deactivated.v1", {
                    "combo_id": str(row.combo_id),
                })

        # Load rates
        for row in SaaSComboRate.objects.select_related("combo").all():
            projection.apply("saas.combo.rate_set.v1", {
                "combo_id": str(row.combo_id),
                "region_code": row.region_code,
                "currency": row.currency,
                "monthly_amount": str(row.monthly_amount),
            })

    @staticmethod
    def save_engine(engine_key, display_name, category, description):
        from core.saas.models import SaaSEngine
        SaaSEngine.objects.update_or_create(
            engine_key=engine_key,
            defaults={
                "display_name": display_name,
                "category": category,
                "description": description,
            },
        )

    @staticmethod
    def save_combo(combo_id, name, slug, description, business_model,
                   paid_engines, max_branches, max_users,
                   max_api_calls_per_month, max_documents_per_month,
                   sort_order, status="ACTIVE"):
        from core.saas.models import SaaSCombo
        SaaSCombo.objects.update_or_create(
            combo_id=combo_id,
            defaults={
                "name": name,
                "slug": slug,
                "description": description,
                "business_model": business_model,
                "paid_engines": paid_engines,
                "max_branches": max_branches,
                "max_users": max_users,
                "max_api_calls_per_month": max_api_calls_per_month,
                "max_documents_per_month": max_documents_per_month,
                "sort_order": sort_order,
                "status": status,
            },
        )

    @staticmethod
    def save_combo_rate(combo_id, region_code, currency, monthly_amount, rate_version):
        from core.saas.models import SaaSComboRate
        SaaSComboRate.objects.update_or_create(
            combo_id=combo_id,
            region_code=region_code,
            defaults={
                "currency": currency,
                "monthly_amount": monthly_amount,
                "rate_version": rate_version,
            },
        )

    @staticmethod
    def deactivate_combo(combo_id):
        from core.saas.models import SaaSCombo
        SaaSCombo.objects.filter(combo_id=combo_id).update(status="DEACTIVATED")

    # =================================================================
    # Rate Governance — trial policy, trial agreements
    # =================================================================

    @staticmethod
    def load_rate_governance_projection(projection) -> None:
        """Load trial policy, agreements, rate changes from DB."""
        from core.saas.models import SaaSTrialPolicy, SaaSTrialAgreement

        # Load trial policy (singleton — latest)
        policy = SaaSTrialPolicy.objects.order_by("-created_at").first()
        if policy:
            projection.apply("saas.trial_policy.set.v1", {
                "default_trial_days": policy.default_trial_days,
                "max_trial_days": policy.max_trial_days,
                "grace_period_days": policy.grace_period_days,
                "rate_notice_days": policy.rate_notice_days,
                "version": policy.version,
            })

        # Load trial agreements
        for row in SaaSTrialAgreement.objects.all():
            projection.apply("saas.trial_agreement.created.v1", {
                "agreement_id": str(row.agreement_id),
                "business_id": str(row.business_id),
                "combo_id": str(row.combo_id) if row.combo_id else "",
                "region_code": row.region_code,
                "currency": row.currency,
                "monthly_amount": str(row.monthly_amount),
                "rate_version": row.rate_version,
                "trial_days": row.trial_days,
                "bonus_days": row.bonus_days,
                "trial_ends_at": row.trial_ends_at,
                "billing_starts_at": row.billing_starts_at,
            })
            if row.status == "CONVERTED":
                projection.apply("saas.trial_agreement.converted.v1", {
                    "agreement_id": str(row.agreement_id),
                    "business_id": str(row.business_id),
                })
            elif row.status == "EXPIRED":
                projection.apply("saas.trial_agreement.expired.v1", {
                    "agreement_id": str(row.agreement_id),
                    "business_id": str(row.business_id),
                })

    @staticmethod
    def save_trial_policy(default_trial_days, max_trial_days, grace_period_days,
                          rate_notice_days, version):
        from core.saas.models import SaaSTrialPolicy
        import uuid
        SaaSTrialPolicy.objects.create(
            id=uuid.uuid4(),
            default_trial_days=default_trial_days,
            max_trial_days=max_trial_days,
            grace_period_days=grace_period_days,
            rate_notice_days=rate_notice_days,
            version=version,
        )

    @staticmethod
    def save_trial_agreement(agreement_id, business_id, combo_id, region_code,
                             currency, monthly_amount, rate_version, trial_days,
                             bonus_days, total_trial_days, trial_ends_at,
                             billing_starts_at, status="ACTIVE"):
        from core.saas.models import SaaSTrialAgreement
        SaaSTrialAgreement.objects.update_or_create(
            agreement_id=agreement_id,
            defaults={
                "business_id": business_id,
                "combo_id": combo_id if combo_id else None,
                "region_code": region_code,
                "currency": currency,
                "monthly_amount": monthly_amount,
                "rate_version": rate_version,
                "trial_days": trial_days,
                "bonus_days": bonus_days,
                "total_trial_days": total_trial_days,
                "trial_ends_at": trial_ends_at,
                "billing_starts_at": billing_starts_at,
                "status": status,
            },
        )

    # =================================================================
    # Subscriptions
    # =================================================================

    @staticmethod
    def load_subscription_projection(projection) -> None:
        """Load subscriptions from DB into the projection."""
        from core.saas.models import SaaSSubscription
        for row in SaaSSubscription.objects.all():
            if row.status == "TRIAL":
                event_type = "saas.subscription.trial_started.v1"
                payload = {
                    "subscription_id": str(row.subscription_id),
                    "business_id": str(row.business_id),
                    "combo_id": str(row.combo_id) if row.combo_id else "",
                    "trial_agreement_id": str(row.trial_agreement_id) if row.trial_agreement_id else "",
                    "billing_starts_at": row.billing_starts_at,
                    "issued_at": row.activated_at,
                }
            else:
                event_type = "saas.subscription.activated.v1"
                payload = {
                    "subscription_id": str(row.subscription_id),
                    "business_id": str(row.business_id),
                    "plan_id": str(row.combo_id) if row.combo_id else "",
                    "combo_id": str(row.combo_id) if row.combo_id else "",
                    "issued_at": row.activated_at,
                }
            projection.apply(event_type, payload)

            # Apply terminal state if needed
            if row.status == "SUSPENDED":
                projection.apply("saas.subscription.suspended.v1", {
                    "business_id": str(row.business_id),
                    "issued_at": row.suspended_at,
                })
            elif row.status == "CANCELLED":
                projection.apply("saas.subscription.cancelled.v1", {
                    "business_id": str(row.business_id),
                    "issued_at": row.cancelled_at,
                })

    @staticmethod
    def save_subscription(subscription_id, business_id, combo_id,
                          trial_agreement_id, status, billing_starts_at,
                          activated_at, renewed_at=None, cancelled_at=None,
                          suspended_at=None, renewal_count=0):
        from core.saas.models import SaaSSubscription
        SaaSSubscription.objects.update_or_create(
            business_id=business_id,
            defaults={
                "subscription_id": subscription_id,
                "combo_id": combo_id,
                "trial_agreement_id": trial_agreement_id,
                "status": status,
                "billing_starts_at": billing_starts_at,
                "activated_at": activated_at,
                "renewed_at": renewed_at,
                "cancelled_at": cancelled_at,
                "suspended_at": suspended_at,
                "renewal_count": renewal_count,
            },
        )

    # =================================================================
    # Promotions
    # =================================================================

    @staticmethod
    def load_promotion_projection(projection) -> None:
        """Load promotions and redemptions from DB into the projection."""
        from core.saas.models import SaaSPromotion, SaaSPromoRedemption
        for row in SaaSPromotion.objects.all():
            projection.apply("saas.promo.created.v1", {
                "promo_id": str(row.promo_id),
                "promo_code": row.promo_code,
                "promo_type": row.promo_type,
                "description": row.description,
                "discount_pct": str(row.discount_pct) if row.discount_pct else None,
                "credit_amount": str(row.credit_amount) if row.credit_amount else None,
                "extra_trial_days": row.extra_trial_days,
                "bonus_engine": row.bonus_engine,
                "max_redemptions": row.max_redemptions,
                "valid_from": row.valid_from,
                "valid_until": row.valid_until,
                "region_code": row.region_code,
                "combo_id": str(row.combo_id) if row.combo_id else None,
            })
            if row.status == "DEACTIVATED":
                projection.apply("saas.promo.deactivated.v1", {
                    "promo_id": str(row.promo_id),
                })

        for row in SaaSPromoRedemption.objects.all():
            projection.apply("saas.promo.redeemed.v1", {
                "promo_id": str(row.promo_id),
                "business_id": str(row.business_id),
                "redeemed_at": row.redeemed_at,
                "details": row.details,
            })

    @staticmethod
    def save_promotion(promo_id, promo_code, promo_type, description="",
                       discount_pct=None, credit_amount=None, extra_trial_days=None,
                       bonus_engine="", max_redemptions=0, valid_from=None,
                       valid_until=None, region_code="", combo_id=None, status="ACTIVE"):
        from core.saas.models import SaaSPromotion
        SaaSPromotion.objects.update_or_create(
            promo_id=promo_id,
            defaults={
                "promo_code": promo_code,
                "promo_type": promo_type,
                "description": description,
                "discount_pct": discount_pct,
                "credit_amount": credit_amount,
                "extra_trial_days": extra_trial_days,
                "bonus_engine": bonus_engine,
                "max_redemptions": max_redemptions,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "region_code": region_code,
                "combo_id": combo_id,
                "status": status,
            },
        )

    @staticmethod
    def save_promo_redemption(promo_id, business_id, redeemed_at, details=None):
        from core.saas.models import SaaSPromoRedemption
        SaaSPromoRedemption.objects.update_or_create(
            promo_id=promo_id,
            business_id=business_id,
            defaults={
                "redeemed_at": redeemed_at,
                "details": details or {},
            },
        )

    @staticmethod
    def update_promo_redemption_count(promo_id, count):
        from core.saas.models import SaaSPromotion
        SaaSPromotion.objects.filter(promo_id=promo_id).update(redemption_count=count)

    @staticmethod
    def deactivate_promo(promo_id):
        from core.saas.models import SaaSPromotion
        SaaSPromotion.objects.filter(promo_id=promo_id).update(status="DEACTIVATED")

    # =================================================================
    # Referrals
    # =================================================================

    @staticmethod
    def load_referral_projection(projection) -> None:
        """Load referral policy, codes, and referrals from DB into the projection."""
        from core.saas.models import SaaSReferralPolicy, SaaSReferralCode, SaaSReferral

        policy = SaaSReferralPolicy.objects.order_by("-created_at").first()
        if policy:
            projection.apply("saas.referral_policy.set.v1", {
                "referrer_reward_days": policy.referrer_reward_days,
                "referee_bonus_days": policy.referee_bonus_days,
                "max_referrals_per_year": policy.max_referrals_per_year,
                "qualification_days": policy.qualification_days,
                "qualification_transactions": policy.qualification_transactions,
            })

        for row in SaaSReferralCode.objects.all():
            projection.apply("saas.referral_code.generated.v1", {
                "business_id": str(row.business_id),
                "code": row.code,
            })

        for row in SaaSReferral.objects.all():
            projection.apply("saas.referral.submitted.v1", {
                "referral_id": str(row.referral_id),
                "referrer_business_id": str(row.referrer_business_id),
                "referee_business_id": str(row.referee_business_id),
                "phone_hash": row.phone_hash,
            })
            if row.status == "QUALIFIED":
                projection.apply("saas.referral.qualified.v1", {
                    "referral_id": str(row.referral_id),
                })
            elif row.status == "REWARDED":
                projection.apply("saas.referral.qualified.v1", {
                    "referral_id": str(row.referral_id),
                })
                projection.apply("saas.referral.rewarded.v1", {
                    "referral_id": str(row.referral_id),
                })
            elif row.status == "REJECTED":
                projection.apply("saas.referral.rejected.v1", {
                    "referral_id": str(row.referral_id),
                })

    @staticmethod
    def save_referral_policy(referrer_reward_days, referee_bonus_days,
                             max_referrals_per_year, qualification_days,
                             qualification_transactions):
        from core.saas.models import SaaSReferralPolicy
        import uuid
        SaaSReferralPolicy.objects.create(
            id=uuid.uuid4(),
            referrer_reward_days=referrer_reward_days,
            referee_bonus_days=referee_bonus_days,
            max_referrals_per_year=max_referrals_per_year,
            qualification_days=qualification_days,
            qualification_transactions=qualification_transactions,
        )

    @staticmethod
    def save_referral_code(business_id, code):
        from core.saas.models import SaaSReferralCode
        SaaSReferralCode.objects.update_or_create(
            business_id=business_id,
            defaults={"code": code},
        )

    @staticmethod
    def save_referral(referral_id, referrer_business_id, referee_business_id,
                      status, phone_hash="", submitted_at=None,
                      qualified_at=None, rewarded_at=None):
        from core.saas.models import SaaSReferral
        SaaSReferral.objects.update_or_create(
            referral_id=referral_id,
            defaults={
                "referrer_business_id": referrer_business_id,
                "referee_business_id": referee_business_id,
                "status": status,
                "phone_hash": phone_hash,
                "submitted_at": submitted_at,
                "qualified_at": qualified_at,
                "rewarded_at": rewarded_at,
            },
        )

    # =================================================================
    # Resellers
    # =================================================================

    @staticmethod
    def load_reseller_projection(projection) -> None:
        """Load resellers, tenant links, commissions, and payouts from DB."""
        from core.saas.models import (
            SaaSReseller, SaaSResellerTenantLink, SaaSCommission, SaaSPayout,
        )

        for row in SaaSReseller.objects.all():
            projection.apply("saas.reseller.registered.v1", {
                "reseller_id": str(row.reseller_id),
                "company_name": row.company_name,
                "contact_name": row.contact_name,
                "contact_phone": row.contact_phone,
                "contact_email": row.contact_email,
                "payout_method": row.payout_method,
                "payout_details": row.payout_details,
            })

        for row in SaaSResellerTenantLink.objects.filter(is_active=True):
            projection.apply("saas.reseller.tenant_linked.v1", {
                "reseller_id": str(row.reseller_id),
                "business_id": str(row.business_id),
            })

        for row in SaaSCommission.objects.order_by("created_at"):
            if row.entry_type == "ACCRUAL":
                projection.apply("saas.reseller.commission_accrued.v1", {
                    "reseller_id": str(row.reseller_id),
                    "business_id": str(row.business_id),
                    "amount": str(row.amount),
                    "currency": row.currency,
                    "period": row.period,
                })
            elif row.entry_type == "CLAWBACK":
                projection.apply("saas.reseller.clawback.v1", {
                    "reseller_id": str(row.reseller_id),
                    "business_id": str(row.business_id),
                    "amount": str(row.amount),
                    "currency": row.currency,
                    "period": row.period,
                })

        for row in SaaSPayout.objects.order_by("created_at"):
            projection.apply("saas.reseller.payout_requested.v1", {
                "payout_id": str(row.payout_id),
                "reseller_id": str(row.reseller_id),
                "amount": str(row.amount),
                "currency": row.currency,
            })
            if row.status == "COMPLETED":
                projection.apply("saas.reseller.payout_completed.v1", {
                    "payout_id": str(row.payout_id),
                })

    @staticmethod
    def save_reseller(reseller_id, company_name, contact_name="",
                      contact_phone="", contact_email="", tier="BRONZE",
                      commission_rate=None, payout_method="",
                      payout_details=None, active_tenant_count=0, status="ACTIVE"):
        from core.saas.models import SaaSReseller
        from decimal import Decimal
        SaaSReseller.objects.update_or_create(
            reseller_id=reseller_id,
            defaults={
                "company_name": company_name,
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "tier": tier,
                "commission_rate": commission_rate or Decimal("0.10"),
                "payout_method": payout_method,
                "payout_details": payout_details or {},
                "active_tenant_count": active_tenant_count,
                "status": status,
            },
        )

    @staticmethod
    def save_reseller_tenant_link(reseller_id, business_id, linked_at, is_active=True):
        from core.saas.models import SaaSResellerTenantLink
        SaaSResellerTenantLink.objects.update_or_create(
            reseller_id=reseller_id,
            business_id=business_id,
            defaults={
                "is_active": is_active,
                "linked_at": linked_at,
            },
        )

    @staticmethod
    def save_commission(reseller_id, business_id, amount, currency, period, entry_type):
        from core.saas.models import SaaSCommission
        import uuid
        SaaSCommission.objects.create(
            id=uuid.uuid4(),
            reseller_id=reseller_id,
            business_id=business_id,
            amount=amount,
            currency=currency,
            period=period,
            entry_type=entry_type,
        )

    @staticmethod
    def save_payout(payout_id, reseller_id, amount, currency, status,
                    requested_at=None, completed_at=None):
        from core.saas.models import SaaSPayout
        SaaSPayout.objects.update_or_create(
            payout_id=payout_id,
            defaults={
                "reseller_id": reseller_id,
                "amount": amount,
                "currency": currency,
                "status": status,
                "requested_at": requested_at,
                "completed_at": completed_at,
            },
        )

    # ── Service-Based Pricing Persistence ──────────────────────

    @staticmethod
    def save_region(code, name, currency, tax_name="VAT", vat_rate=0.0,
                    digital_tax_rate=0.0, b2b_reverse_charge=False,
                    registration_required=True, is_active=True, **_kw):
        from core.saas.models import SaaSRegion
        SaaSRegion.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "currency": currency,
                "tax_name": tax_name,
                "vat_rate": vat_rate,
                "digital_tax_rate": digital_tax_rate,
                "b2b_reverse_charge": b2b_reverse_charge,
                "registration_required": registration_required,
                "is_active": is_active,
            },
        )

    @staticmethod
    def save_service_rate(service_key, region_code, currency, monthly_amount,
                          **_kw):
        from core.saas.models import SaaSServiceRate
        SaaSServiceRate.objects.update_or_create(
            service_key=service_key,
            region_code=region_code,
            defaults={
                "currency": currency,
                "monthly_amount": monthly_amount,
            },
        )

    @staticmethod
    def save_service_toggle(service_key, active, **_kw):
        from core.saas.models import SaaSServiceToggle
        SaaSServiceToggle.objects.update_or_create(
            service_key=service_key,
            defaults={"active": active},
        )

    @staticmethod
    def save_capacity_rate(dimension, tier_key, region_code, currency,
                           monthly_amount, **_kw):
        from core.saas.models import SaaSCapacityRate
        SaaSCapacityRate.objects.update_or_create(
            dimension=dimension,
            tier_key=tier_key,
            region_code=region_code,
            defaults={
                "currency": currency,
                "monthly_amount": monthly_amount,
            },
        )

    @staticmethod
    def save_reduction_rate(region_code, service_count, reduction_pct, **_kw):
        from core.saas.models import SaaSReductionRate
        SaaSReductionRate.objects.update_or_create(
            region_code=region_code,
            service_count=service_count,
            defaults={"reduction_pct": reduction_pct},
        )

    @staticmethod
    def load_pricing_projection(proj):
        """Hydrate a ServicePricingProjection from the DB."""
        from core.saas.models import (
            SaaSRegion, SaaSServiceRate, SaaSServiceToggle,
            SaaSCapacityRate, SaaSReductionRate,
        )

        for r in SaaSRegion.objects.all():
            proj.apply("saas.region.added.v1", {
                "code": r.code,
                "name": r.name,
                "currency": r.currency,
                "tax_name": r.tax_name,
                "vat_rate": r.vat_rate,
                "digital_tax_rate": r.digital_tax_rate,
                "b2b_reverse_charge": r.b2b_reverse_charge,
                "registration_required": r.registration_required,
                "is_active": r.is_active,
            })

        for sr in SaaSServiceRate.objects.all():
            proj.apply("saas.service.rate_set.v1", {
                "service_key": sr.service_key,
                "region_code": sr.region_code,
                "currency": sr.currency,
                "monthly_amount": str(sr.monthly_amount),
            })

        for st in SaaSServiceToggle.objects.all():
            proj.apply("saas.service.toggled.v1", {
                "service_key": st.service_key,
                "active": st.active,
            })

        for cr in SaaSCapacityRate.objects.all():
            proj.apply("saas.capacity.rate_set.v1", {
                "dimension": cr.dimension,
                "tier_key": cr.tier_key,
                "region_code": cr.region_code,
                "currency": cr.currency,
                "monthly_amount": str(cr.monthly_amount),
            })

        for rr in SaaSReductionRate.objects.all():
            proj.apply("saas.reduction.rate_set.v1", {
                "region_code": rr.region_code,
                "service_count": rr.service_count,
                "reduction_pct": str(rr.reduction_pct),
            })
