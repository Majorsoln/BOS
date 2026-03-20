"""
BOS SaaS Models - Django ORM
============================
Persistent models for the SaaS billing, trial, subscription, promotion,
referral, and reseller subsystems.
"""

from __future__ import annotations

import uuid

from django.db import models


# ---------------------------------------------------------------------------
# TextChoices enums
# ---------------------------------------------------------------------------

class EngineCategory(models.TextChoices):
    FREE = "FREE", "Free"
    PAID = "PAID", "Paid"


class BusinessModel(models.TextChoices):
    B2B = "B2B", "B2B"
    B2C = "B2C", "B2C"
    BOTH = "BOTH", "Both"


class ComboStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


class TrialAgreementStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CONVERTED = "CONVERTED", "Converted"
    EXPIRED = "EXPIRED", "Expired"


class SubscriptionStatus(models.TextChoices):
    TRIAL = "TRIAL", "Trial"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    CANCELLED = "CANCELLED", "Cancelled"


class PromoType(models.TextChoices):
    DISCOUNT = "DISCOUNT", "Discount"
    CREDIT = "CREDIT", "Credit"
    EXTENDED_TRIAL = "EXTENDED_TRIAL", "Extended Trial"
    ENGINE_BONUS = "ENGINE_BONUS", "Engine Bonus"
    BUNDLE_DISCOUNT = "BUNDLE_DISCOUNT", "Bundle Discount"


class PromoStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DEACTIVATED = "DEACTIVATED", "Deactivated"
    EXHAUSTED = "EXHAUSTED", "Exhausted"


class ReferralStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    QUALIFIED = "QUALIFIED", "Qualified"
    REWARDED = "REWARDED", "Rewarded"
    REJECTED = "REJECTED", "Rejected"


class ResellerTier(models.TextChoices):
    BRONZE = "BRONZE", "Bronze"
    SILVER = "SILVER", "Silver"
    GOLD = "GOLD", "Gold"


class ResellerStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


class CommissionEntryType(models.TextChoices):
    ACCRUAL = "ACCRUAL", "Accrual"
    CLAWBACK = "CLAWBACK", "Clawback"


class PayoutStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


# ---------------------------------------------------------------------------
# 1. SaaSEngine — engine catalog
# ---------------------------------------------------------------------------

class SaaSEngine(models.Model):
    engine_key = models.CharField(max_length=64, primary_key=True)
    display_name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=16,
        choices=EngineCategory.choices,
        default=EngineCategory.PAID,
    )
    description = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_engine"
        ordering = ["engine_key"]

    def __str__(self) -> str:
        return f"{self.engine_key} ({self.category})"


# ---------------------------------------------------------------------------
# 2. SaaSCombo — combo definitions
# ---------------------------------------------------------------------------

class SaaSCombo(models.Model):
    combo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=128, unique=True)
    description = models.TextField(default="", blank=True)
    business_model = models.CharField(
        max_length=8,
        choices=BusinessModel.choices,
        default=BusinessModel.BOTH,
    )
    paid_engines = models.JSONField(default=list)
    max_branches = models.IntegerField(default=1)
    max_users = models.IntegerField(default=3)
    max_api_calls_per_month = models.IntegerField(default=5000)
    max_documents_per_month = models.IntegerField(default=500)
    sort_order = models.IntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=ComboStatus.choices,
        default=ComboStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_combo"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["status"], name="idx_saas_combo_status"),
            models.Index(
                fields=["business_model", "status"],
                name="idx_saas_combo_bmodel_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


# ---------------------------------------------------------------------------
# 3. SaaSComboRate — per-region pricing
# ---------------------------------------------------------------------------

class SaaSComboRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    combo = models.ForeignKey(
        SaaSCombo,
        on_delete=models.PROTECT,
        related_name="rates",
        db_column="combo_id",
    )
    region_code = models.CharField(max_length=8)
    currency = models.CharField(max_length=8)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    rate_version = models.IntegerField(default=1)
    effective_from = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_combo_rate"
        ordering = ["combo_id", "region_code"]
        indexes = [
            models.Index(
                fields=["combo", "region_code"],
                name="idx_saas_crate_combo_region",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["combo", "region_code"],
                name="uq_saas_combo_rate_combo_region",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.combo_id} {self.region_code} {self.currency} {self.monthly_amount}"


# ---------------------------------------------------------------------------
# 4. SaaSTrialPolicy — platform singleton
# ---------------------------------------------------------------------------

class SaaSTrialPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    default_trial_days = models.IntegerField(default=180)
    max_trial_days = models.IntegerField(default=365)
    grace_period_days = models.IntegerField(default=7)
    rate_notice_days = models.IntegerField(default=90)
    version = models.CharField(max_length=32, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_trial_policy"

    def __str__(self) -> str:
        return f"TrialPolicy v{self.version} ({self.default_trial_days}d)"


# ---------------------------------------------------------------------------
# 5. SaaSTrialAgreement — immutable per-business
# ---------------------------------------------------------------------------

class SaaSTrialAgreement(models.Model):
    agreement_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    business_id = models.UUIDField(db_index=True)
    combo = models.ForeignKey(
        SaaSCombo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trial_agreements",
        db_column="combo_id",
    )
    region_code = models.CharField(max_length=8)
    currency = models.CharField(max_length=8)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    rate_version = models.IntegerField(default=1)
    trial_days = models.IntegerField()
    bonus_days = models.IntegerField(default=0)
    total_trial_days = models.IntegerField()
    trial_ends_at = models.DateTimeField()
    billing_starts_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=TrialAgreementStatus.choices,
        default=TrialAgreementStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bos_saas_trial_agreement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["business_id"],
                name="idx_saas_tagr_business",
            ),
            models.Index(
                fields=["status"],
                name="idx_saas_tagr_status",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"TrialAgreement {self.agreement_id} "
            f"biz={self.business_id} ({self.status})"
        )


# ---------------------------------------------------------------------------
# 6. SaaSSubscription — one per business
# ---------------------------------------------------------------------------

class SaaSSubscription(models.Model):
    subscription_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    business_id = models.UUIDField(unique=True, db_index=True)
    combo = models.ForeignKey(
        SaaSCombo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        db_column="combo_id",
    )
    trial_agreement = models.ForeignKey(
        SaaSTrialAgreement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        db_column="trial_agreement_id",
    )
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    billing_starts_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    renewed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    renewal_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_subscription"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["business_id"],
                name="idx_saas_sub_business",
            ),
            models.Index(
                fields=["status"],
                name="idx_saas_sub_status",
            ),
            models.Index(
                fields=["combo", "status"],
                name="idx_saas_sub_combo_status",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Subscription {self.subscription_id} "
            f"biz={self.business_id} ({self.status})"
        )


# ---------------------------------------------------------------------------
# 7. SaaSPromotion — promo definitions
# ---------------------------------------------------------------------------

class SaaSPromotion(models.Model):
    promo_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    promo_code = models.CharField(max_length=64, unique=True)
    promo_type = models.CharField(
        max_length=24,
        choices=PromoType.choices,
    )
    description = models.TextField(default="", blank=True)
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    credit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_trial_days = models.IntegerField(null=True, blank=True)
    bonus_engine = models.CharField(max_length=64, default="", blank=True)
    max_redemptions = models.IntegerField(default=0)
    redemption_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    region_code = models.CharField(max_length=8, default="", blank=True)
    combo = models.ForeignKey(
        SaaSCombo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
        db_column="combo_id",
    )
    status = models.CharField(
        max_length=16,
        choices=PromoStatus.choices,
        default=PromoStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_promotion"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["promo_code"],
                name="idx_saas_promo_code",
            ),
            models.Index(
                fields=["status"],
                name="idx_saas_promo_status",
            ),
            models.Index(
                fields=["promo_type", "status"],
                name="idx_saas_promo_type_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.promo_code} ({self.promo_type} / {self.status})"


# ---------------------------------------------------------------------------
# 8. SaaSPromoRedemption — promo usage tracking
# ---------------------------------------------------------------------------

class SaaSPromoRedemption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo = models.ForeignKey(
        SaaSPromotion,
        on_delete=models.PROTECT,
        related_name="redemptions",
        db_column="promo_id",
    )
    business_id = models.UUIDField()
    redeemed_at = models.DateTimeField()
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "bos_saas_promo_redemption"
        ordering = ["-redeemed_at"]
        indexes = [
            models.Index(
                fields=["business_id"],
                name="idx_saas_predem_business",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["promo", "business_id"],
                name="uq_saas_promo_redemption_promo_biz",
            ),
        ]

    def __str__(self) -> str:
        return f"Redemption {self.promo_id} by {self.business_id}"


# ---------------------------------------------------------------------------
# 9. SaaSReferralPolicy — platform singleton
# ---------------------------------------------------------------------------

class SaaSReferralPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer_reward_days = models.IntegerField(default=30)
    referee_bonus_days = models.IntegerField(default=30)
    max_referrals_per_year = models.IntegerField(default=12)
    qualification_days = models.IntegerField(default=30)
    qualification_transactions = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_referral_policy"

    def __str__(self) -> str:
        return (
            f"ReferralPolicy reward={self.referrer_reward_days}d "
            f"max={self.max_referrals_per_year}/yr"
        )


# ---------------------------------------------------------------------------
# 10. SaaSReferralCode — per-business
# ---------------------------------------------------------------------------

class SaaSReferralCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_id = models.UUIDField(unique=True)
    code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bos_saas_referral_code"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["business_id"],
                name="idx_saas_rcode_business",
            ),
            models.Index(
                fields=["code"],
                name="idx_saas_rcode_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} (biz={self.business_id})"


# ---------------------------------------------------------------------------
# 11. SaaSReferral — referral records
# ---------------------------------------------------------------------------

class SaaSReferral(models.Model):
    referral_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    referrer_business_id = models.UUIDField()
    referee_business_id = models.UUIDField()
    status = models.CharField(
        max_length=16,
        choices=ReferralStatus.choices,
        default=ReferralStatus.PENDING,
    )
    phone_hash = models.CharField(max_length=128, default="", blank=True)
    submitted_at = models.DateTimeField()
    qualified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_referral"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(
                fields=["referrer_business_id"],
                name="idx_saas_ref_referrer",
            ),
            models.Index(
                fields=["referee_business_id"],
                name="idx_saas_ref_referee",
            ),
            models.Index(
                fields=["status"],
                name="idx_saas_ref_status",
            ),
            models.Index(
                fields=["phone_hash"],
                name="idx_saas_ref_phone_hash",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Referral {self.referral_id} "
            f"{self.referrer_business_id} -> {self.referee_business_id} ({self.status})"
        )


# ---------------------------------------------------------------------------
# 12. SaaSReseller — reseller records
# ---------------------------------------------------------------------------

class SaaSReseller(models.Model):
    reseller_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, default="", blank=True)
    contact_phone = models.CharField(max_length=64, default="", blank=True)
    contact_email = models.CharField(max_length=255, default="", blank=True)
    tier = models.CharField(
        max_length=8,
        choices=ResellerTier.choices,
        default=ResellerTier.BRONZE,
    )
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4)
    payout_method = models.CharField(max_length=32, default="", blank=True)
    payout_details = models.JSONField(default=dict, blank=True)
    active_tenant_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=ResellerStatus.choices,
        default=ResellerStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_reseller"
        ordering = ["company_name"]
        indexes = [
            models.Index(
                fields=["status"],
                name="idx_saas_resl_status",
            ),
            models.Index(
                fields=["tier", "status"],
                name="idx_saas_resl_tier_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.tier} / {self.status})"


# ---------------------------------------------------------------------------
# 13. SaaSResellerTenantLink — tenant-reseller mapping
# ---------------------------------------------------------------------------

class SaaSResellerTenantLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reseller = models.ForeignKey(
        SaaSReseller,
        on_delete=models.PROTECT,
        related_name="tenant_links",
        db_column="reseller_id",
    )
    business_id = models.UUIDField()
    is_active = models.BooleanField(default=True)
    linked_at = models.DateTimeField()

    class Meta:
        db_table = "bos_saas_reseller_tenant_link"
        ordering = ["-linked_at"]
        indexes = [
            models.Index(
                fields=["business_id"],
                name="idx_saas_rtlink_business",
            ),
            models.Index(
                fields=["reseller", "is_active"],
                name="idx_saas_rtlink_resl_active",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reseller", "business_id"],
                name="uq_saas_reseller_tenant_link",
            ),
        ]

    def __str__(self) -> str:
        return f"Reseller {self.reseller_id} <-> Biz {self.business_id}"


# ---------------------------------------------------------------------------
# 14. SaaSCommission — commission entries
# ---------------------------------------------------------------------------

class SaaSCommission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reseller = models.ForeignKey(
        SaaSReseller,
        on_delete=models.PROTECT,
        related_name="commissions",
        db_column="reseller_id",
    )
    business_id = models.UUIDField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    period = models.CharField(max_length=32)
    entry_type = models.CharField(
        max_length=16,
        choices=CommissionEntryType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bos_saas_commission"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["reseller", "period"],
                name="idx_saas_comm_resl_period",
            ),
            models.Index(
                fields=["business_id"],
                name="idx_saas_comm_business",
            ),
            models.Index(
                fields=["entry_type"],
                name="idx_saas_comm_entry_type",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Commission {self.entry_type} {self.amount} {self.currency} "
            f"reseller={self.reseller_id} period={self.period}"
        )


# ---------------------------------------------------------------------------
# 15. SaaSPayout — payout records
# ---------------------------------------------------------------------------

class SaaSPayout(models.Model):
    payout_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    reseller = models.ForeignKey(
        SaaSReseller,
        on_delete=models.PROTECT,
        related_name="payouts",
        db_column="reseller_id",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    status = models.CharField(
        max_length=16,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
    )
    requested_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_payout"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["reseller", "status"],
                name="idx_saas_payout_resl_status",
            ),
            models.Index(
                fields=["status"],
                name="idx_saas_payout_status",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Payout {self.payout_id} {self.amount} {self.currency} "
            f"({self.status})"
        )
