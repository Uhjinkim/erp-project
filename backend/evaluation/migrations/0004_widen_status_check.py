# The shared ERP database already has CHECK chk_evaluations_status allowing only 작성중/확정,
# which rejects the README workflow states (제출, 반려, 제외). This migration replaces it with
# a check over all five states and records the constraint in Django's model state.
# PostgreSQL only: other databases get the constraint from the model state when created.

from django.db import migrations, models

STATUSES = ["작성중", "제출", "반려", "확정", "제외"]
LEGACY_STATUSES = ["작성중", "확정"]


def _replace_check(schema_editor, statuses):
    if schema_editor.connection.vendor != "postgresql":
        return
    allowed = ", ".join(f"'{status}'" for status in statuses)
    schema_editor.execute(
        "ALTER TABLE evaluations DROP CONSTRAINT IF EXISTS chk_evaluations_status"
    )
    schema_editor.execute(
        "ALTER TABLE evaluations ADD CONSTRAINT chk_evaluations_status "
        f"CHECK (eval_status IN ({allowed}))"
    )


def widen(apps, schema_editor):
    _replace_check(schema_editor, STATUSES)


def restore(apps, schema_editor):
    _replace_check(schema_editor, LEGACY_STATUSES)


class Migration(migrations.Migration):
    dependencies = [
        ("evaluation", "0003_history_changed_at_timestamp"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(widen, restore)],
            state_operations=[
                migrations.AddConstraint(
                    model_name="evaluationmodel",
                    constraint=models.CheckConstraint(
                        condition=models.Q(eval_status__in=STATUSES),
                        name="chk_evaluations_status",
                    ),
                ),
            ],
        ),
    ]
