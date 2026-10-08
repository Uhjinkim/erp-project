from django.db import migrations


def create_bonus_component(apps, schema_editor):
    component_type = apps.get_model("payroll", "PayrollComponentTypeModel")
    component_type.objects.get_or_create(
        code="BONUS",
        defaults={"name": "상여", "category": "지급"},
    )


class Migration(migrations.Migration):
    dependencies = [("payroll", "0003_seed_components")]

    operations = [migrations.RunPython(create_bonus_component, migrations.RunPython.noop)]
