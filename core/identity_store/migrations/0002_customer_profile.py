from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core_identity_store", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                (
                    "business_customer_id",
                    models.UUIDField(
                        primary_key=True, editable=False, serialize=False
                    ),
                ),
                (
                    "business",
                    models.ForeignKey(
                        db_column="business_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="customer_profiles",
                        to="core_identity_store.business",
                    ),
                ),
                (
                    "global_customer_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Platform-level customer UUID (empty for walk-in / manual entry).",
                        max_length=255,
                    ),
                ),
                ("display_name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, default="", max_length=64)),
                ("email", models.CharField(blank=True, default="", max_length=255)),
                ("address", models.CharField(blank=True, default="", max_length=512)),
                ("segment", models.CharField(blank=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_identity_customer_profiles",
                "ordering": ["business_id", "display_name"],
            },
        ),
        migrations.AddIndex(
            model_name="customerprofile",
            index=models.Index(
                fields=["business", "global_customer_id"],
                name="idx_cust_profile_biz_global",
            ),
        ),
    ]
