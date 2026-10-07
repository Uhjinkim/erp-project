from django.db import migrations


def create_income_tax_component(apps, schema_editor):
    component_type = apps.get_model("payroll", "PayrollComponentTypeModel")
    component_type.objects.get_or_create(
        code="INCOME_TAX",
        defaults={"name": "소득세(지방소득세 포함)", "category": "공제"},
    )


class Migration(migrations.Migration):
    dependencies = [("payroll", "0004_seed_bonus_component")]

    operations = [migrations.RunPython(create_income_tax_component, migrations.RunPython.noop)]
