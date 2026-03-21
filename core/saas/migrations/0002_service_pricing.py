import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("saas", "0001_saas_initial"),
    ]

    operations = [
        # ── 16. SaaSRegion ────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSRegion",
            fields=[
                ("code", models.CharField(max_length=8, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("currency", models.CharField(max_length=8)),
                ("tax_name", models.CharField(default="VAT", max_length=32)),
                ("vat_rate", models.FloatField(default=0.0)),
                ("digital_tax_rate", models.FloatField(default=0.0)),
                ("b2b_reverse_charge", models.BooleanField(default=False)),
                ("registration_required", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_region",
                "ordering": ["code"],
            },
        ),
        # ── 17. SaaSServiceRate ───────────────────────────────────
        migrations.CreateModel(
            name="SaaSServiceRate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("service_key", models.CharField(max_length=64)),
                ("region_code", models.CharField(max_length=8)),
                ("currency", models.CharField(max_length=8)),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_service_rate",
                "ordering": ["service_key", "region_code"],
            },
        ),
        migrations.AddConstraint(
            model_name="saasservicerate",
            constraint=models.UniqueConstraint(
                fields=["service_key", "region_code"],
                name="uq_saas_service_rate_svc_region",
            ),
        ),
        migrations.AddIndex(
            model_name="saasservicerate",
            index=models.Index(fields=["service_key"], name="idx_saas_svcrate_svc"),
        ),
        migrations.AddIndex(
            model_name="saasservicerate",
            index=models.Index(fields=["region_code"], name="idx_saas_svcrate_region"),
        ),
        # ── 18. SaaSServiceToggle ─────────────────────────────────
        migrations.CreateModel(
            name="SaaSServiceToggle",
            fields=[
                ("service_key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_service_toggle",
                "ordering": ["service_key"],
            },
        ),
        # ── 19. SaaSCapacityRate ──────────────────────────────────
        migrations.CreateModel(
            name="SaaSCapacityRate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("dimension", models.CharField(max_length=64)),
                ("tier_key", models.CharField(max_length=64)),
                ("region_code", models.CharField(max_length=8)),
                ("currency", models.CharField(max_length=8)),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_capacity_rate",
                "ordering": ["dimension", "tier_key", "region_code"],
            },
        ),
        migrations.AddConstraint(
            model_name="saascapacityrate",
            constraint=models.UniqueConstraint(
                fields=["dimension", "tier_key", "region_code"],
                name="uq_saas_capacity_rate_dim_tier_region",
            ),
        ),
        migrations.AddIndex(
            model_name="saascapacityrate",
            index=models.Index(fields=["dimension"], name="idx_saas_caprate_dim"),
        ),
        migrations.AddIndex(
            model_name="saascapacityrate",
            index=models.Index(fields=["region_code"], name="idx_saas_caprate_region"),
        ),
        # ── 20. SaaSReductionRate ─────────────────────────────────
        migrations.CreateModel(
            name="SaaSReductionRate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("region_code", models.CharField(max_length=8)),
                ("service_count", models.IntegerField()),
                ("reduction_pct", models.DecimalField(decimal_places=2, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_reduction_rate",
                "ordering": ["region_code", "service_count"],
            },
        ),
        migrations.AddConstraint(
            model_name="saasreductionrate",
            constraint=models.UniqueConstraint(
                fields=["region_code", "service_count"],
                name="uq_saas_reduction_rate_region_count",
            ),
        ),
        migrations.AddIndex(
            model_name="saasreductionrate",
            index=models.Index(fields=["region_code"], name="idx_saas_redrate_region"),
        ),
    ]
