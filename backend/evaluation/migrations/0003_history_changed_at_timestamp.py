# Changes evaluation_history.changed_at from timestamptz to timestamp (without time zone),
# as the evaluation README specifies. Applied to the shared database with the other
# evaluation migrations; existing values are converted in the UTC session time zone.

from django.db import migrations

import evaluation.infrastructure.fields


class Migration(migrations.Migration):
    dependencies = [
        ("evaluation", "0002_evaluation_workflow"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evaluationhistorymodel",
            name="changed_at",
            field=evaluation.infrastructure.fields.TimestampField(),
        ),
    ]
