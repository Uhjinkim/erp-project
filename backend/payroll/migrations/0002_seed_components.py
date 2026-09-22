from django.db import migrations

DEFAULT_COMPONENTS = [
    ("BASE_PAY", "기본급", "지급", 10),
    ("FIXED_ALLOWANCE", "고정수당", "지급", 20),
    ("OVERTIME_ALLOWANCE", "초과근무수당", "지급", 30),
    ("NATIONAL_PENSION", "국민연금", "공제", 40),
    ("HEALTH_INSURANCE", "건강보험(장기요양보험 포함)", "공제", 50),
    ("EMPLOYMENT_INSURANCE", "고용보험", "공제", 60),
]


def create_default_components(apps, schema_editor):
    component_type = apps.get_model("payroll", "PayrollComponentTypeModel")
    for code, name, category, sort_order in DEFAULT_COMPONENTS:
        component_type.objects.get_or_create(
            code=code,
            defaults={"name": name, "category": category, "sort_order": sort_order},
        )


class Migration(migrations.Migration):
    dependencies = [("payroll", "0001_initial")]

    operations = [migrations.RunPython(create_default_components, migrations.RunPython.noop)]
