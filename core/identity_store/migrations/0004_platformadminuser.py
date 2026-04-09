from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity_store", "0003_customerprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformAdminUser",
            fields=[
                ("admin_id", models.UUIDField(primary_key=True, editable=False, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(unique=True)),
                ("role", models.CharField(
                    choices=[
                        ("SUPER_ADMIN", "Super Admin"),
                        ("FINANCE_ADMIN", "Finance Admin"),
                        ("AGENT_MANAGER", "Agent Manager"),
                        ("COMPLIANCE_OFFICER", "Compliance Officer"),
                        ("VIEWER", "Viewer"),
                    ],
                    default="VIEWER",
                    max_length=30,
                )),
                ("status", models.CharField(
                    choices=[("ACTIVE", "Active"), ("SUSPENDED", "Suspended")],
                    default="ACTIVE",
                    max_length=20,
                )),
                ("api_key_hash", models.CharField(blank=True, default="", max_length=64, unique=True)),
                ("created_by", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_active_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "bos_platform_admin_users",
                "ordering": ["role", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="platformadminuser",
            index=models.Index(fields=["role", "status"], name="idx_padmin_role_status"),
        ),
        migrations.AddIndex(
            model_name="platformadminuser",
            index=models.Index(fields=["email"], name="idx_padmin_email"),
        ),
    ]
