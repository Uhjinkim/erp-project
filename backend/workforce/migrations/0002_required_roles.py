from django.db import migrations


def create_required_roles(apps, schema_editor):
    role = apps.get_model("workforce", "Role")
    for role_code, role_name in (
        ("HR_MANAGER", "인사 관리자"),
        ("HR_LEAVE_APPROVER", "휴가 승인 인사담당자"),
    ):
        role.objects.get_or_create(
            role_code=role_code,
            defaults={"role_name": role_name},
        )


class Migration(migrations.Migration):
    dependencies = [("workforce", "0001_initial")]

    operations = [migrations.RunPython(create_required_roles, migrations.RunPython.noop)]
