from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core_identity_store", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("permission_key", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "role",
                    models.ForeignKey(
                        db_column="role_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="role_permissions",
                        to="core_identity_store.role",
                    ),
                ),
            ],
            options={
                "db_table": "bos_role_permissions",
                "ordering": ["role_id", "permission_key", "id"],
                "indexes": [
                    models.Index(fields=["permission_key"], name="idx_role_perm_key"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("role", "permission_key"),
                        name="uq_role_permission",
                    ),
                ],
            },
        ),
    ]
