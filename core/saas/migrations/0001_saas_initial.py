import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        # ── 1. SaaSEngine ──────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSEngine",
            fields=[
                ("engine_key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("display_name", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[("FREE", "Free"), ("PAID", "Paid")],
                        default="PAID",
                        max_length=16,
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_engine",
                "ordering": ["engine_key"],
            },
        ),
        # ── 2. SaaSCombo ───────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSCombo",
            fields=[
                ("combo_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.CharField(max_length=128, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "business_model",
                    models.CharField(
                        choices=[("B2B", "B2B"), ("B2C", "B2C"), ("BOTH", "Both")],
                        default="BOTH",
                        max_length=8,
                    ),
                ),
                ("paid_engines", models.JSONField(default=list)),
                ("max_branches", models.IntegerField(default=1)),
                ("max_users", models.IntegerField(default=3)),
                ("max_api_calls_per_month", models.IntegerField(default=5000)),
                ("max_documents_per_month", models.IntegerField(default=500)),
                ("sort_order", models.IntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("DEACTIVATED", "Deactivated")],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_combo",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="saascombo",
            index=models.Index(fields=["status"], name="idx_saas_combo_status"),
        ),
        migrations.AddIndex(
            model_name="saascombo",
            index=models.Index(fields=["business_model", "status"], name="idx_saas_combo_bmodel_status"),
        ),
        # ── 3. SaaSComboRate ───────────────────────────────────────
        migrations.CreateModel(
            name="SaaSComboRate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "combo",
                    models.ForeignKey(
                        db_column="combo_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rates",
                        to="core_saas.saascombo",
                    ),
                ),
                ("region_code", models.CharField(max_length=8)),
                ("currency", models.CharField(max_length=8)),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("rate_version", models.IntegerField(default=1)),
                ("effective_from", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_combo_rate",
                "ordering": ["combo_id", "region_code"],
            },
        ),
        migrations.AddIndex(
            model_name="saascomborate",
            index=models.Index(fields=["combo", "region_code"], name="idx_saas_crate_combo_region"),
        ),
        migrations.AddConstraint(
            model_name="saascomborate",
            constraint=models.UniqueConstraint(fields=("combo", "region_code"), name="uq_saas_combo_rate_combo_region"),
        ),
        # ── 4. SaaSTrialPolicy ─────────────────────────────────────
        migrations.CreateModel(
            name="SaaSTrialPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("default_trial_days", models.IntegerField(default=180)),
                ("max_trial_days", models.IntegerField(default=365)),
                ("grace_period_days", models.IntegerField(default=7)),
                ("rate_notice_days", models.IntegerField(default=90)),
                ("version", models.CharField(blank=True, default="", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_trial_policy",
            },
        ),
        # ── 5. SaaSTrialAgreement ──────────────────────────────────
        migrations.CreateModel(
            name="SaaSTrialAgreement",
            fields=[
                ("agreement_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("business_id", models.UUIDField(db_index=True)),
                (
                    "combo",
                    models.ForeignKey(
                        blank=True,
                        db_column="combo_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trial_agreements",
                        to="core_saas.saascombo",
                    ),
                ),
                ("region_code", models.CharField(max_length=8)),
                ("currency", models.CharField(max_length=8)),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("rate_version", models.IntegerField(default=1)),
                ("trial_days", models.IntegerField()),
                ("bonus_days", models.IntegerField(default=0)),
                ("total_trial_days", models.IntegerField()),
                ("trial_ends_at", models.DateTimeField()),
                ("billing_starts_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("CONVERTED", "Converted"), ("EXPIRED", "Expired")],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "bos_saas_trial_agreement",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saastrialagreement",
            index=models.Index(fields=["business_id"], name="idx_saas_tagr_business"),
        ),
        migrations.AddIndex(
            model_name="saastrialagreement",
            index=models.Index(fields=["status"], name="idx_saas_tagr_status"),
        ),
        # ── 6. SaaSSubscription ────────────────────────────────────
        migrations.CreateModel(
            name="SaaSSubscription",
            fields=[
                ("subscription_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("business_id", models.UUIDField(db_index=True, unique=True)),
                (
                    "combo",
                    models.ForeignKey(
                        blank=True,
                        db_column="combo_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subscriptions",
                        to="core_saas.saascombo",
                    ),
                ),
                (
                    "trial_agreement",
                    models.ForeignKey(
                        blank=True,
                        db_column="trial_agreement_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subscriptions",
                        to="core_saas.saastrialagreement",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("TRIAL", "Trial"),
                            ("ACTIVE", "Active"),
                            ("SUSPENDED", "Suspended"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="TRIAL",
                        max_length=16,
                    ),
                ),
                ("billing_starts_at", models.DateTimeField(blank=True, null=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("renewed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("suspended_at", models.DateTimeField(blank=True, null=True)),
                ("renewal_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_subscription",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saassubscription",
            index=models.Index(fields=["business_id"], name="idx_saas_sub_business"),
        ),
        migrations.AddIndex(
            model_name="saassubscription",
            index=models.Index(fields=["status"], name="idx_saas_sub_status"),
        ),
        migrations.AddIndex(
            model_name="saassubscription",
            index=models.Index(fields=["combo", "status"], name="idx_saas_sub_combo_status"),
        ),
        # ── 7. SaaSPromotion ───────────────────────────────────────
        migrations.CreateModel(
            name="SaaSPromotion",
            fields=[
                ("promo_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("promo_code", models.CharField(max_length=64, unique=True)),
                (
                    "promo_type",
                    models.CharField(
                        choices=[
                            ("DISCOUNT", "Discount"),
                            ("CREDIT", "Credit"),
                            ("EXTENDED_TRIAL", "Extended Trial"),
                            ("ENGINE_BONUS", "Engine Bonus"),
                            ("BUNDLE_DISCOUNT", "Bundle Discount"),
                        ],
                        max_length=24,
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("discount_pct", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("credit_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("extra_trial_days", models.IntegerField(blank=True, null=True)),
                ("bonus_engine", models.CharField(blank=True, default="", max_length=64)),
                ("max_redemptions", models.IntegerField(default=0)),
                ("redemption_count", models.IntegerField(default=0)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("region_code", models.CharField(blank=True, default="", max_length=8)),
                (
                    "combo",
                    models.ForeignKey(
                        blank=True,
                        db_column="combo_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="promotions",
                        to="core_saas.saascombo",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("DEACTIVATED", "Deactivated"),
                            ("EXHAUSTED", "Exhausted"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_promotion",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saaspromotion",
            index=models.Index(fields=["promo_code"], name="idx_saas_promo_code"),
        ),
        migrations.AddIndex(
            model_name="saaspromotion",
            index=models.Index(fields=["status"], name="idx_saas_promo_status"),
        ),
        migrations.AddIndex(
            model_name="saaspromotion",
            index=models.Index(fields=["promo_type", "status"], name="idx_saas_promo_type_status"),
        ),
        # ── 8. SaaSPromoRedemption ─────────────────────────────────
        migrations.CreateModel(
            name="SaaSPromoRedemption",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "promo",
                    models.ForeignKey(
                        db_column="promo_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="redemptions",
                        to="core_saas.saaspromotion",
                    ),
                ),
                ("business_id", models.UUIDField()),
                ("redeemed_at", models.DateTimeField()),
                ("details", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "db_table": "bos_saas_promo_redemption",
                "ordering": ["-redeemed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saaspromoredemption",
            index=models.Index(fields=["business_id"], name="idx_saas_predem_business"),
        ),
        migrations.AddConstraint(
            model_name="saaspromoredemption",
            constraint=models.UniqueConstraint(fields=("promo", "business_id"), name="uq_saas_promo_redemption_promo_biz"),
        ),
        # ── 9. SaaSReferralPolicy ──────────────────────────────────
        migrations.CreateModel(
            name="SaaSReferralPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("referrer_reward_days", models.IntegerField(default=30)),
                ("referee_bonus_days", models.IntegerField(default=30)),
                ("max_referrals_per_year", models.IntegerField(default=12)),
                ("qualification_days", models.IntegerField(default=30)),
                ("qualification_transactions", models.IntegerField(default=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_referral_policy",
            },
        ),
        # ── 10. SaaSReferralCode ───────────────────────────────────
        migrations.CreateModel(
            name="SaaSReferralCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("business_id", models.UUIDField(unique=True)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "bos_saas_referral_code",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saasreferralcode",
            index=models.Index(fields=["business_id"], name="idx_saas_rcode_business"),
        ),
        migrations.AddIndex(
            model_name="saasreferralcode",
            index=models.Index(fields=["code"], name="idx_saas_rcode_code"),
        ),
        # ── 11. SaaSReferral ───────────────────────────────────────
        migrations.CreateModel(
            name="SaaSReferral",
            fields=[
                ("referral_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("referrer_business_id", models.UUIDField()),
                ("referee_business_id", models.UUIDField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("QUALIFIED", "Qualified"),
                            ("REWARDED", "Rewarded"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("phone_hash", models.CharField(blank=True, default="", max_length=128)),
                ("submitted_at", models.DateTimeField()),
                ("qualified_at", models.DateTimeField(blank=True, null=True)),
                ("rewarded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_referral",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saasreferral",
            index=models.Index(fields=["referrer_business_id"], name="idx_saas_ref_referrer"),
        ),
        migrations.AddIndex(
            model_name="saasreferral",
            index=models.Index(fields=["referee_business_id"], name="idx_saas_ref_referee"),
        ),
        migrations.AddIndex(
            model_name="saasreferral",
            index=models.Index(fields=["status"], name="idx_saas_ref_status"),
        ),
        migrations.AddIndex(
            model_name="saasreferral",
            index=models.Index(fields=["phone_hash"], name="idx_saas_ref_phone_hash"),
        ),
        # ── 12. SaaSReseller ───────────────────────────────────────
        migrations.CreateModel(
            name="SaaSReseller",
            fields=[
                ("reseller_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_name", models.CharField(max_length=255)),
                ("contact_name", models.CharField(blank=True, default="", max_length=255)),
                ("contact_phone", models.CharField(blank=True, default="", max_length=64)),
                ("contact_email", models.CharField(blank=True, default="", max_length=255)),
                (
                    "tier",
                    models.CharField(
                        choices=[("BRONZE", "Bronze"), ("SILVER", "Silver"), ("GOLD", "Gold")],
                        default="BRONZE",
                        max_length=8,
                    ),
                ),
                ("commission_rate", models.DecimalField(decimal_places=4, max_digits=5)),
                ("payout_method", models.CharField(blank=True, default="", max_length=32)),
                ("payout_details", models.JSONField(blank=True, default=dict)),
                ("active_tenant_count", models.IntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("DEACTIVATED", "Deactivated")],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_reseller",
                "ordering": ["company_name"],
            },
        ),
        migrations.AddIndex(
            model_name="saasreseller",
            index=models.Index(fields=["status"], name="idx_saas_resl_status"),
        ),
        migrations.AddIndex(
            model_name="saasreseller",
            index=models.Index(fields=["tier", "status"], name="idx_saas_resl_tier_status"),
        ),
        # ── 13. SaaSResellerTenantLink ─────────────────────────────
        migrations.CreateModel(
            name="SaaSResellerTenantLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "reseller",
                    models.ForeignKey(
                        db_column="reseller_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tenant_links",
                        to="core_saas.saasreseller",
                    ),
                ),
                ("business_id", models.UUIDField()),
                ("is_active", models.BooleanField(default=True)),
                ("linked_at", models.DateTimeField()),
            ],
            options={
                "db_table": "bos_saas_reseller_tenant_link",
                "ordering": ["-linked_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saasresellertenantlink",
            index=models.Index(fields=["business_id"], name="idx_saas_rtlink_business"),
        ),
        migrations.AddIndex(
            model_name="saasresellertenantlink",
            index=models.Index(fields=["reseller", "is_active"], name="idx_saas_rtlink_resl_active"),
        ),
        migrations.AddConstraint(
            model_name="saasresellertenantlink",
            constraint=models.UniqueConstraint(fields=("reseller", "business_id"), name="uq_saas_reseller_tenant_link"),
        ),
        # ── 14. SaaSCommission ─────────────────────────────────────
        migrations.CreateModel(
            name="SaaSCommission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "reseller",
                    models.ForeignKey(
                        db_column="reseller_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="commissions",
                        to="core_saas.saasreseller",
                    ),
                ),
                ("business_id", models.UUIDField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(max_length=8)),
                ("period", models.CharField(max_length=32)),
                (
                    "entry_type",
                    models.CharField(
                        choices=[("ACCRUAL", "Accrual"), ("CLAWBACK", "Clawback")],
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "bos_saas_commission",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saascommission",
            index=models.Index(fields=["reseller", "period"], name="idx_saas_comm_resl_period"),
        ),
        migrations.AddIndex(
            model_name="saascommission",
            index=models.Index(fields=["business_id"], name="idx_saas_comm_business"),
        ),
        migrations.AddIndex(
            model_name="saascommission",
            index=models.Index(fields=["entry_type"], name="idx_saas_comm_entry_type"),
        ),
        # ── 15. SaaSPayout ─────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSPayout",
            fields=[
                ("payout_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "reseller",
                    models.ForeignKey(
                        db_column="reseller_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payouts",
                        to="core_saas.saasreseller",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("requested_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_payout",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddIndex(
            model_name="saaspayout",
            index=models.Index(fields=["reseller", "status"], name="idx_saas_payout_resl_status"),
        ),
        migrations.AddIndex(
            model_name="saaspayout",
            index=models.Index(fields=["status"], name="idx_saas_payout_status"),
        ),
    ]
