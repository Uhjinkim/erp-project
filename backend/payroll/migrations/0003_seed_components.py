from django.db import migrations

# 담당자 확인(2026-09-23): 지급 항목은 기본급+고정수당, 변동수당(초과근무수당 등), 공제 항목은
# 4대보험. item_type 허용값은 '지급'/'공제' 두 가지(payroll_items.chk_payroll_items_type).
DEFAULT_COMPONENTS = [
    ("BASE_PAY", "기본급", "지급"),
    ("FIXED_ALLOWANCE", "고정수당", "지급"),
    ("OVERTIME_ALLOWANCE", "초과근무수당", "지급"),
    ("NATIONAL_PENSION", "국민연금", "공제"),
    ("HEALTH_INSURANCE", "건강보험(장기요양보험 포함)", "공제"),
    ("EMPLOYMENT_INSURANCE", "고용보험", "공제"),
]


def create_default_components(apps, schema_editor):
    component_type = apps.get_model("payroll", "PayrollComponentTypeModel")
    for code, name, category in DEFAULT_COMPONENTS:
        component_type.objects.get_or_create(
            code=code,
            defaults={"name": name, "category": category},
        )


class Migration(migrations.Migration):
    dependencies = [("payroll", "0002_public_holiday")]

    operations = [migrations.RunPython(create_default_components, migrations.RunPython.noop)]
