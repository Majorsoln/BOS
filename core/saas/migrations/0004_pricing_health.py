"""
Migration: Add SaaSPricingGovernanceBound, SaaSRlaServicePrice, SaaSRlaHealthScore

- PricingGovernanceBound: Platform sets min/max per service per region
- RlaServicePrice: RLA's actual price per service (validated against bounds)
- RlaHealthScore: Composite health metric (remittance + growth + escalations + activity)
"""

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0003_agentcontract"),
    ]

    operations = [
        # ── 24. SaaSPricingGovernanceBound ───────────────────────────────────
        migrations.CreateModel(
            name="SaaSPricingGovernanceBound",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("service_key", models.CharField(max_length=128, help_text="e.g. 'retail', 'restaurant'")),
                ("region_code", models.CharField(max_length=8)),
                ("currency", models.CharField(max_length=8)),
                ("min_amount", models.BigIntegerField(default=0, help_text="Min price in minor currency units")),
                ("max_amount", models.BigIntegerField(default=9999999, help_text="Max price in minor currency units")),
                ("set_by", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "bos_saas_pricing_governance", "ordering": ["region_code", "service_key"]},
        ),
        migrations.AddConstraint(
            model_name="saaspricinggovernancebound",
            constraint=models.UniqueConstraint(fields=["service_key", "region_code"], name="uq_saas_pricegov_service_region"),
        ),
        migrations.AddIndex(
            model_name="saaspricinggovernancebound",
            index=models.Index(fields=["region_code"], name="idx_saas_pricegov_region"),
        ),
        migrations.AddIndex(
            model_name="saaspricinggovernancebound",
            index=models.Index(fields=["service_key"], name="idx_saas_pricegov_service"),
        ),

        # ── 25. SaaSRlaServicePrice ──────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSRlaServicePrice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("agent_id", models.UUIDField(db_index=True)),
                ("region_code", models.CharField(default="", max_length=8)),
                ("service_key", models.CharField(max_length=128)),
                ("amount", models.BigIntegerField(help_text="Price in minor currency units")),
                ("currency", models.CharField(max_length=8)),
                ("set_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "bos_saas_rla_service_price", "ordering": ["agent_id", "service_key"]},
        ),
        migrations.AddConstraint(
            model_name="saasrlaserviceprice",
            constraint=models.UniqueConstraint(fields=["agent_id", "service_key"], name="uq_saas_rla_price_agent_service"),
        ),
        migrations.AddIndex(
            model_name="saasrlaserviceprice",
            index=models.Index(fields=["agent_id"], name="idx_saas_rlaprice_agent"),
        ),
        migrations.AddIndex(
            model_name="saasrlaserviceprice",
            index=models.Index(fields=["region_code"], name="idx_saas_rlaprice_region"),
        ),

        # ── 26. SaaSRlaHealthScore ───────────────────────────────────────────
        migrations.CreateModel(
            name="SaaSRlaHealthScore",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("agent_id", models.UUIDField(db_index=True)),
                ("region_code", models.CharField(default="", max_length=8)),
                ("period", models.CharField(max_length=8, help_text="YYYY-MM")),
                ("total_score", models.IntegerField(default=0, help_text="0-100")),
                ("grade", models.CharField(
                    choices=[
                        ("GREEN", "Green  — Healthy (80–100)"),
                        ("AMBER", "Amber  — Watch (60–79)"),
                        ("ORANGE", "Orange — At Risk (40–59)"),
                        ("RED", "Red    — Action Required (20–39)"),
                        ("BLACK", "Black  — Critical / Suspended (0–19)"),
                    ],
                    default="GREEN",
                    max_length=8,
                )),
                ("remittance_score", models.IntegerField(default=40)),
                ("growth_score", models.IntegerField(default=25)),
                ("escalation_score", models.IntegerField(default=20)),
                ("activity_score", models.IntegerField(default=15)),
                ("overdue_remittances", models.IntegerField(default=0)),
                ("active_tenants", models.IntegerField(default=0)),
                ("tenant_target", models.IntegerField(default=0)),
                ("open_escalations", models.IntegerField(default=0)),
                ("days_since_active", models.IntegerField(default=0)),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "bos_saas_rla_health_score", "ordering": ["-period", "agent_id"]},
        ),
        migrations.AddConstraint(
            model_name="saasrlahealthscore",
            constraint=models.UniqueConstraint(fields=["agent_id", "period"], name="uq_saas_health_agent_period"),
        ),
        migrations.AddIndex(
            model_name="saasrlahealthscore",
            index=models.Index(fields=["agent_id"], name="idx_saas_health_agent"),
        ),
        migrations.AddIndex(
            model_name="saasrlahealthscore",
            index=models.Index(fields=["grade"], name="idx_saas_health_grade"),
        ),
        migrations.AddIndex(
            model_name="saasrlahealthscore",
            index=models.Index(fields=["period"], name="idx_saas_health_period"),
        ),
    ]
