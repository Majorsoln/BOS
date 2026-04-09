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


# ---------------------------------------------------------------------------
# 16. SaaSRegion — dynamic region/country configuration
# ---------------------------------------------------------------------------

class RegionStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PILOT = "PILOT", "Pilot"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    SUNSET = "SUNSET", "Sunset"


class SaaSRegion(models.Model):
    code = models.CharField(max_length=8, primary_key=True)
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=8)
    status = models.CharField(
        max_length=16,
        choices=RegionStatusChoices.choices,
        default=RegionStatusChoices.ACTIVE,
    )

    # ── Tax & Compliance ──
    tax_name = models.CharField(max_length=32, default="VAT")
    vat_rate = models.FloatField(default=0.0)
    digital_tax_rate = models.FloatField(default=0.0)
    b2b_reverse_charge = models.BooleanField(default=False)
    registration_required = models.BooleanField(default=True)
    regulatory_body = models.CharField(max_length=128, default="", blank=True)
    business_license_required = models.BooleanField(default=True)
    data_residency_required = models.BooleanField(default=False)

    # ── Financial ──
    min_payout_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    payout_currency = models.CharField(max_length=8, default="", blank=True)

    # ── Operations ──
    default_language = models.CharField(max_length=8, default="en")
    timezone = models.CharField(max_length=64, default="Africa/Nairobi")
    support_phone = models.CharField(max_length=32, default="", blank=True)
    support_email = models.CharField(max_length=255, default="", blank=True)
    support_hours = models.CharField(max_length=128, default="", blank=True)
    country_calling_code = models.CharField(max_length=8, default="", blank=True)
    phone_format = models.CharField(max_length=64, default="", blank=True)

    # ── Launch Management ──
    launched_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    sunset_at = models.DateTimeField(null=True, blank=True)
    pilot_tenant_limit = models.IntegerField(default=0)
    launch_notes = models.TextField(default="", blank=True)

    # ── Legacy ──
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_region"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["status"], name="idx_saas_region_status"),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name} ({self.currency}) [{self.status}]"


# ---------------------------------------------------------------------------
# 16b. SaaSRegionPaymentChannel — payment collection methods per region
# ---------------------------------------------------------------------------

class SaaSRegionPaymentChannel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        SaaSRegion,
        on_delete=models.CASCADE,
        related_name="payment_channels_set",
        db_column="region_code",
    )
    channel_key = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255)
    provider = models.CharField(max_length=64)
    channel_type = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, default=999999999)
    settlement_delay_days = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_region_payment_channel"
        ordering = ["region", "channel_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "channel_key"],
                name="uq_saas_region_payment_channel",
            ),
        ]
        indexes = [
            models.Index(
                fields=["region", "is_active"],
                name="idx_saas_rpc_region_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.region_id}/{self.channel_key} ({self.provider})"


# ---------------------------------------------------------------------------
# 16c. SaaSRegionSettlementAccount — bank accounts for fund settlement
# ---------------------------------------------------------------------------

class SaaSRegionSettlementAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        SaaSRegion,
        on_delete=models.CASCADE,
        related_name="settlement_accounts_set",
        db_column="region_code",
    )
    bank_name = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=64)
    branch_code = models.CharField(max_length=32, default="", blank=True)
    swift_code = models.CharField(max_length=16, default="", blank=True)
    currency = models.CharField(max_length=8)
    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_region_settlement_account"
        ordering = ["region", "-is_primary"]
        indexes = [
            models.Index(
                fields=["region", "is_primary"],
                name="idx_saas_rsa_region_primary",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.region_id} {self.bank_name} ({self.account_number})"


# ---------------------------------------------------------------------------
# 17. SaaSServiceRate — monthly rate per service per region
# ---------------------------------------------------------------------------

class SaaSServiceRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_key = models.CharField(max_length=64)
    region_code = models.CharField(max_length=8)
    currency = models.CharField(max_length=8)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_service_rate"
        ordering = ["service_key", "region_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_key", "region_code"],
                name="uq_saas_service_rate_svc_region",
            ),
        ]
        indexes = [
            models.Index(
                fields=["service_key"],
                name="idx_saas_svcrate_svc",
            ),
            models.Index(
                fields=["region_code"],
                name="idx_saas_svcrate_region",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service_key} @ {self.region_code} = {self.monthly_amount} {self.currency}"


# ---------------------------------------------------------------------------
# 18. SaaSServiceToggle — active/inactive flag per service
# ---------------------------------------------------------------------------

class SaaSServiceToggle(models.Model):
    service_key = models.CharField(max_length=64, primary_key=True)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_service_toggle"
        ordering = ["service_key"]

    def __str__(self) -> str:
        return f"{self.service_key} active={self.active}"


# ---------------------------------------------------------------------------
# 19. SaaSCapacityRate — tiered pricing per dimension per region
# ---------------------------------------------------------------------------

class SaaSCapacityRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dimension = models.CharField(max_length=64)
    tier_key = models.CharField(max_length=64)
    region_code = models.CharField(max_length=8)
    currency = models.CharField(max_length=8)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_capacity_rate"
        ordering = ["dimension", "tier_key", "region_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["dimension", "tier_key", "region_code"],
                name="uq_saas_capacity_rate_dim_tier_region",
            ),
        ]
        indexes = [
            models.Index(
                fields=["dimension"],
                name="idx_saas_caprate_dim",
            ),
            models.Index(
                fields=["region_code"],
                name="idx_saas_caprate_region",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dimension}/{self.tier_key} @ {self.region_code} = {self.monthly_amount} {self.currency}"


# ---------------------------------------------------------------------------
# 20. SaaSReductionRate — multi-service discount per region
# ---------------------------------------------------------------------------

class SaaSReductionRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region_code = models.CharField(max_length=8)
    service_count = models.IntegerField()
    reduction_pct = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_reduction_rate"
        ordering = ["region_code", "service_count"]
        constraints = [
            models.UniqueConstraint(
                fields=["region_code", "service_count"],
                name="uq_saas_reduction_rate_region_count",
            ),
        ]
        indexes = [
            models.Index(
                fields=["region_code"],
                name="idx_saas_redrate_region",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.region_code} {self.service_count} services = {self.reduction_pct}% off"


# ---------------------------------------------------------------------------
# 21. SaaSRegionalManager — one per region
# ---------------------------------------------------------------------------

class SaaSRegionalManager(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region_code = models.CharField(max_length=8, unique=True)
    reseller = models.ForeignKey(
        SaaSReseller,
        on_delete=models.PROTECT,
        related_name="managed_regions",
        db_column="reseller_id",
    )
    bonus_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.03)
    total_bonus_earned = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    appointed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_regional_manager"
        ordering = ["region_code"]
        indexes = [
            models.Index(
                fields=["reseller"],
                name="idx_saas_rmgr_reseller",
            ),
        ]

    def __str__(self) -> str:
        return f"RegionalManager {self.region_code} → reseller={self.reseller_id}"


# ---------------------------------------------------------------------------
# 22. SaaSTerritory — named sub-areas within a region
# ---------------------------------------------------------------------------

class SaaSTerritory(models.Model):
    territory_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    region_code = models.CharField(max_length=8)
    territory_name = models.CharField(max_length=255)
    reseller = models.ForeignKey(
        SaaSReseller,
        on_delete=models.PROTECT,
        related_name="territories",
        db_column="reseller_id",
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_territory"
        ordering = ["region_code", "territory_name"]
        indexes = [
            models.Index(
                fields=["region_code", "is_active"],
                name="idx_saas_terr_region_active",
            ),
            models.Index(
                fields=["reseller", "is_active"],
                name="idx_saas_terr_resl_active",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["region_code", "territory_name"],
                name="uq_saas_territory_region_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.territory_name} ({self.region_code}) → reseller={self.reseller_id}"


# ---------------------------------------------------------------------------
# 23. SaaSRegionalCommissionOverride — per-region commission adjustment
# ---------------------------------------------------------------------------

class SaaSRegionalCommissionOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region_code = models.CharField(max_length=8, unique=True)
    override_rate = models.DecimalField(max_digits=5, decimal_places=4)
    reason = models.TextField(default="", blank=True)
    set_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_regional_commission_override"
        ordering = ["region_code"]

    def __str__(self) -> str:
        return f"{self.region_code} override={self.override_rate}"


# ---------------------------------------------------------------------------
# 24. SaaSRegionalTarget — monthly targets per region
# ---------------------------------------------------------------------------

class SaaSRegionalTarget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region_code = models.CharField(max_length=8)
    period = models.CharField(max_length=16)
    target_tenant_count = models.IntegerField(default=0)
    target_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8)
    set_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_regional_target"
        ordering = ["region_code", "-period"]
        constraints = [
            models.UniqueConstraint(
                fields=["region_code", "period"],
                name="uq_saas_regional_target_region_period",
            ),
        ]
        indexes = [
            models.Index(
                fields=["region_code"],
                name="idx_saas_rtarget_region",
            ),
            models.Index(
                fields=["period"],
                name="idx_saas_rtarget_period",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Target {self.region_code}/{self.period}: "
            f"{self.target_tenant_count} tenants, {self.target_revenue} {self.currency}"
        )


# ---------------------------------------------------------------------------
# 22. AgentContractStatus / TerminationType — enums for RLA contracts
# ---------------------------------------------------------------------------

class AgentContractStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    TERMINATED_REVERSIBLE = "TERMINATED_REVERSIBLE", "Terminated (Reversible)"
    TERMINATED_PERMANENT = "TERMINATED_PERMANENT", "Terminated (Permanent)"
    REDUCED_COMMISSION = "REDUCED_COMMISSION", "Reduced Commission (Reinstated)"
    EXPIRED = "EXPIRED", "Expired"


class TerminationType(models.TextChoices):
    REVERSIBLE = "REVERSIBLE", "Reversible — can be reinstated to full terms"
    PERMANENT = "PERMANENT", "Permanent — licence revoked, never reinstated"
    REDUCED_COMMISSION = "REDUCED_COMMISSION", "Reduced Commission — reinstated at lower share under term"


# ---------------------------------------------------------------------------
# 23. AgentContract — Platform-generated RLA franchise agreement
# ---------------------------------------------------------------------------
# BOS Doctrine: Platform is Franchisor. RLA is Franchisee with guided autonomy.
# Contract has HARDCODED terms (non-negotiable) and GENERATED terms
# (commission rate, region, targets — set at appointment time).
#
# Three termination outcomes (franchisor doctrine):
#   REVERSIBLE   — violation allows reinstatement to full terms
#   PERMANENT    — serious breach; licence permanently revoked
#   REDUCED      — reinstated but at reduced commission share under fixed term
#
# During any termination: tenants continue service without billing until
# a new RLA is assigned to the region.
# ---------------------------------------------------------------------------

class AgentContract(models.Model):
    contract_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Which agent this contract governs
    agent_id = models.UUIDField(db_index=True)
    agent_name = models.CharField(max_length=255, default="")
    region_code = models.CharField(max_length=8)

    # Contract lifecycle
    status = models.CharField(
        max_length=30,
        choices=AgentContractStatus.choices,
        default=AgentContractStatus.DRAFT,
    )
    version = models.IntegerField(default=1)

    # Termination metadata (populated only when terminated)
    termination_type = models.CharField(
        max_length=20,
        choices=TerminationType.choices,
        blank=True,
        default="",
    )
    termination_reason = models.TextField(blank=True, default="")
    terminated_by = models.UUIDField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)

    # Hardcoded platform terms (non-negotiable — serialised as JSON)
    # These cannot be changed by the RLA. They include:
    #   - remittance_deadline_days: 5 (RLA must remit within 5 days of collection)
    #   - tenant_continuity_guaranteed: true (tenants never lose access due to RLA termination)
    #   - region_exclusivity: true (one active RLA per region)
    #   - platform_audit_right: true (platform can audit RLA records at any time)
    #   - compliance_ownership: true (RLA owns all regional compliance filings)
    #   - sub_agent_requires_approval: true (RLA cannot appoint sub-agents without platform approval)
    #   - price_bound_enforcement: true (RLA must price within platform min/max)
    hardcoded_terms = models.JSONField(default=dict, blank=True)

    # Generated / configurable terms (set at appointment — negotiated)
    # Includes:
    #   - commission_rate: e.g. 0.30 (30% market share)
    #   - max_platform_discount_pct: e.g. 15
    #   - max_trial_days: e.g. 180
    #   - performance_targets: {monthly_tenant_target, monthly_revenue_target}
    #   - contract_duration_months: e.g. 24
    #   - reduced_commission_rate (only when status=REDUCED_COMMISSION)
    generated_terms = models.JSONField(default=dict, blank=True)

    # Reduced-commission reinstatement terms (populated only for REDUCED_COMMISSION outcome)
    reduced_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True,
        help_text="Commission rate during reduced-commission reinstatement period"
    )
    reduced_commission_term_months = models.IntegerField(
        null=True, blank=True,
        help_text="Number of months the reduced-commission term lasts"
    )
    reduced_commission_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the reduced-commission term ends (normal rates resume)"
    )

    # Signing workflow
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_to_agent_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by_name = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)

    # Tenant continuity tracking
    # When RLA is terminated, this region enters PENDING_RLA state.
    # Tenants continue service — no billing until new RLA assigned.
    region_pending_rla_since = models.DateTimeField(
        null=True, blank=True,
        help_text="Set when RLA terminated; cleared when new RLA takes over region"
    )

    # Audit
    generated_by = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_saas_agent_contract"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent_id"], name="idx_saas_contract_agent"),
            models.Index(fields=["region_code"], name="idx_saas_contract_region"),
            models.Index(fields=["status"], name="idx_saas_contract_status"),
            models.Index(fields=["termination_type"], name="idx_saas_contract_term_type"),
        ]

    def __str__(self) -> str:
        return f"Contract {self.contract_id} | {self.region_code} | {self.status}"
