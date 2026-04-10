"""
Migration: Add AgentContract model for Platform-RLA franchise agreements.

BOS Doctrine:
  - Platform = Franchisor, RLA = Franchisee with guided autonomy
  - Contracts have hardcoded terms (non-negotiable) + generated terms (negotiated)
  - Three termination outcomes: REVERSIBLE, PERMANENT, REDUCED_COMMISSION
  - Tenant continuity guaranteed during any RLA termination gap
"""

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core_saas", "0002_service_pricing"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentContract",
            fields=[
                ("contract_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("agent_id", models.UUIDField(db_index=True)),
                ("agent_name", models.CharField(default="", max_length=255)),
                ("region_code", models.CharField(max_length=8)),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"),
                        ("ACTIVE", "Active"),
                        ("SUSPENDED", "Suspended"),
                        ("TERMINATED_REVERSIBLE", "Terminated (Reversible)"),
                        ("TERMINATED_PERMANENT", "Terminated (Permanent)"),
                        ("REDUCED_COMMISSION", "Reduced Commission (Reinstated)"),
                        ("EXPIRED", "Expired"),
                    ],
                    default="DRAFT",
                    max_length=30,
                )),
                ("version", models.IntegerField(default=1)),
                ("termination_type", models.CharField(
                    blank=True,
                    choices=[
                        ("REVERSIBLE", "Reversible — can be reinstated to full terms"),
                        ("PERMANENT", "Permanent — licence revoked, never reinstated"),
                        ("REDUCED_COMMISSION", "Reduced Commission — reinstated at lower share under term"),
                    ],
                    default="",
                    max_length=20,
                )),
                ("termination_reason", models.TextField(blank=True, default="")),
                ("terminated_by", models.UUIDField(blank=True, null=True)),
                ("terminated_at", models.DateTimeField(blank=True, null=True)),
                ("hardcoded_terms", models.JSONField(blank=True, default=dict)),
                ("generated_terms", models.JSONField(blank=True, default=dict)),
                ("reduced_commission_rate", models.DecimalField(
                    blank=True,
                    decimal_places=4,
                    help_text="Commission rate during reduced-commission reinstatement period",
                    max_digits=5,
                    null=True,
                )),
                ("reduced_commission_term_months", models.IntegerField(
                    blank=True,
                    help_text="Number of months the reduced-commission term lasts",
                    null=True,
                )),
                ("reduced_commission_expires_at", models.DateTimeField(
                    blank=True,
                    help_text="When the reduced-commission term ends (normal rates resume)",
                    null=True,
                )),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("sent_to_agent_at", models.DateTimeField(blank=True, null=True)),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                ("signed_by_name", models.CharField(blank=True, default="", max_length=255)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("region_pending_rla_since", models.DateTimeField(
                    blank=True,
                    help_text="Set when RLA terminated; cleared when new RLA takes over region",
                    null=True,
                )),
                ("generated_by", models.UUIDField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_saas_agent_contract",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="agentcontract",
            index=models.Index(fields=["agent_id"], name="idx_saas_contract_agent"),
        ),
        migrations.AddIndex(
            model_name="agentcontract",
            index=models.Index(fields=["region_code"], name="idx_saas_contract_region"),
        ),
        migrations.AddIndex(
            model_name="agentcontract",
            index=models.Index(fields=["status"], name="idx_saas_contract_status"),
        ),
        migrations.AddIndex(
            model_name="agentcontract",
            index=models.Index(fields=["termination_type"], name="idx_saas_contract_term_type"),
        ),
    ]
