import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApiKeyCredential",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "key_hash",
                    models.CharField(
                        db_index=True,
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("label", models.CharField(blank=True, default="", max_length=255)),
                ("actor_id", models.CharField(max_length=255)),
                (
                    "actor_type",
                    models.CharField(
                        choices=[
                            ("HUMAN", "Human"),
                            ("SYSTEM", "System"),
                            ("DEVICE", "Device"),
                            ("AI", "AI"),
                        ],
                        max_length=20,
                    ),
                ),
                ("allowed_business_ids", models.JSONField(default=list)),
                ("allowed_branch_ids_by_business", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("REVOKED", "Revoked")],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_actor_id", models.CharField(max_length=255)),
                (
                    "revoked_by_actor_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            options={
                "db_table": "bos_api_key_credentials",
                "ordering": ["created_at", "id"],
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"],
                        name="idx_api_key_status_created",
                    )
                ],
            },
        ),
    ]
