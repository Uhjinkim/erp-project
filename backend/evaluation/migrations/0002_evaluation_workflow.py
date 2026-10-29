# Unlike 0001 (state-only), this migration changes the shared database: it adds
# evaluations.created_by, a unique (emp_no, eval_year) constraint and the
# evaluation_history table. It is applied when the feature branches are merged.
# Before applying, check read-only that evaluations has no duplicate (emp_no, eval_year)
# rows, otherwise AddConstraint fails.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evaluation", "0001_initial"),
        ("workforce", "0002_required_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationHistoryModel",
            fields=[
                ("history_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=20)),
                ("from_status", models.CharField(blank=True, max_length=20, null=True)),
                ("to_status", models.CharField(max_length=20)),
                (
                    "score",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
                ),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("changed_at", models.DateTimeField()),
            ],
            options={
                "db_table": "evaluation_history",
                "ordering": ["changed_at", "history_id"],
            },
        ),
        migrations.AddField(
            model_name="evaluationmodel",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                db_column="created_by",
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="created_evaluations",
                to="workforce.employee",
            ),
        ),
        migrations.AlterField(
            model_name="evaluationmodel",
            name="eval_status",
            field=models.CharField(
                choices=[
                    ("작성중", "작성중"),
                    ("제출", "제출"),
                    ("반려", "반려"),
                    ("확정", "확정"),
                    ("제외", "제외"),
                ],
                default="작성중",
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="evaluationmodel",
            constraint=models.UniqueConstraint(
                fields=("employee", "eval_year"), name="uq_evaluations_emp_no_eval_year"
            ),
        ),
        migrations.AddField(
            model_name="evaluationhistorymodel",
            name="actor",
            field=models.ForeignKey(
                db_column="actor_emp_no",
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="evaluation_actions",
                to="workforce.employee",
            ),
        ),
        migrations.AddField(
            model_name="evaluationhistorymodel",
            name="evaluation",
            field=models.ForeignKey(
                db_column="eval_id",
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="history_entries",
                to="evaluation.evaluationmodel",
            ),
        ),
        migrations.AddField(
            model_name="evaluationhistorymodel",
            name="from_evaluator",
            field=models.ForeignKey(
                blank=True,
                db_column="from_evaluator_no",
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="+",
                to="workforce.employee",
            ),
        ),
        migrations.AddField(
            model_name="evaluationhistorymodel",
            name="to_evaluator",
            field=models.ForeignKey(
                blank=True,
                db_column="to_evaluator_no",
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="+",
                to="workforce.employee",
            ),
        ),
    ]
