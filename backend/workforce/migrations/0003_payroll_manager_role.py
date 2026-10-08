from django.db import migrations


def create_payroll_manager_role(apps, schema_editor):
    role = apps.get_model("workforce", "Role")
    role.objects.get_or_create(
        role_code="PAYROLL_MANAGER",
        defaults={"role_name": "급여 담당자"},
    )


class Migration(migrations.Migration):
    dependencies = [("workforce", "0002_required_roles")]

    operations = [migrations.RunPython(create_payroll_manager_role, migrations.RunPython.noop)]
