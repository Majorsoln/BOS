from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Actor",
            fields=[
                ("actor_id", models.CharField(max_length=255, primary_key=True, serialize=False)),
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
                ("display_name", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_identity_actors",
                "ordering": ["actor_id"],
            },
        ),
        migrations.CreateModel(
            name="Business",
            fields=[
                ("business_id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("default_currency", models.CharField(default="USD", max_length=16)),
                ("default_language", models.CharField(default="en", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "bos_identity_businesses",
                "ordering": ["business_id"],
            },
        ),
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("branch_id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "business",
                    models.ForeignKey(
                        db_column="business_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="branches",
                        to="core_identity_store.business",
                    ),
                ),
            ],
            options={
                "db_table": "bos_identity_branches",
                "ordering": ["business_id", "branch_id"],
                "indexes": [
                    models.Index(fields=["business", "branch_id"], name="idx_branch_biz_branch"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("role_id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "business",
                    models.ForeignKey(
                        db_column="business_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="roles",
                        to="core_identity_store.business",
                    ),
                ),
            ],
            options={
                "db_table": "bos_identity_roles",
                "ordering": ["business_id", "name", "role_id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("business", "name"),
                        name="uq_identity_role_business_name",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "actor",
                    models.ForeignKey(
                        db_column="actor_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="role_assignments",
                        to="core_identity_store.actor",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        db_column="branch_id",
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="role_assignments",
                        to="core_identity_store.branch",
                    ),
                ),
                (
                    "business",
                    models.ForeignKey(
                        db_column="business_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="role_assignments",
                        to="core_identity_store.business",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        db_column="role_id",
                        on_delete=models.deletion.PROTECT,
                        related_name="assignments",
                        to="core_identity_store.role",
                    ),
                ),
            ],
            options={
                "db_table": "bos_identity_role_assignments",
                "ordering": ["business_id", "actor_id", "branch_id", "role_id", "id"],
                "indexes": [
                    models.Index(
                        fields=["business", "actor", "status"],
                        name="idx_role_asg_biz_actor_status",
                    ),
                    models.Index(
                        fields=["business", "branch", "status"],
                        name="idx_role_asg_biz_branch_status",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("business", "branch", "actor", "role"),
                        name="uq_identity_role_assignment",
                    ),
                ],
            },
        ),
    ]
