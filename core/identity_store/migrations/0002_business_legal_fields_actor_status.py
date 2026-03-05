from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core_identity_store", "0001_initial"),
    ]

    operations = [
        # Business legal/compliance fields
        migrations.AddField(
            model_name="business",
            name="address",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="business",
            name="city",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="business",
            name="country_code",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AddField(
            model_name="business",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="business",
            name="email",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="business",
            name="tax_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="business",
            name="logo_url",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        # Actor status field (AD-22)
        migrations.AddField(
            model_name="actor",
            name="status",
            field=models.CharField(
                choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                default="ACTIVE",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="actor",
            index=models.Index(fields=["status"], name="idx_actor_status"),
        ),
    ]
