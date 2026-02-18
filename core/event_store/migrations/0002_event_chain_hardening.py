from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("event_store", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["business_id", "created_at", "event_id"],
                name="idx_evt_biz_created_id",
            ),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["business_id", "event_id"],
                name="idx_evt_biz_event_id",
            ),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["business_id", "branch_id", "created_at"],
                name="idx_evt_biz_branch_created",
            ),
        ),
        migrations.AddConstraint(
            model_name="event",
            constraint=models.UniqueConstraint(
                fields=("business_id", "previous_event_hash"),
                name="uq_evt_biz_prev_hash",
            ),
        ),
    ]
