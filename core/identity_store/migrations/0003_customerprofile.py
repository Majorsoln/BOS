from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("core_identity_store", "0002_business_legal_fields_actor_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                (
                    "customer_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("display_name", models.CharField(max_length=255)),
                (
                    "phone",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "email",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "address",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("INACTIVE", "Inactive"),
                        ],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "business",
                    models.ForeignKey(
                        db_column="business_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="customer_profiles",
                        to="core_identity_store.business",
                    ),
                ),
            ],
            options={
                "db_table": "bos_identity_customer_profiles",
                "ordering": ["business_id", "display_name"],
                "indexes": [
                    models.Index(
                        fields=["business", "status"],
                        name="idx_custprof_biz_status",
                    ),
                    models.Index(
                        fields=["business", "phone"],
                        name="idx_custprof_biz_phone",
                    ),
                ],
            },
        ),
    ]
