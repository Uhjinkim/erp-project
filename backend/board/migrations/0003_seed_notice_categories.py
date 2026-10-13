from django.db import migrations


def create_notice_categories(apps, schema_editor):
    category = apps.get_model("board", "NoticeCategoryModel")
    for code, name in (
        ("MANAGEMENT", "경영"),
        ("HR", "인사"),
        ("PAYROLL", "급여"),
    ):
        category.objects.get_or_create(
            notice_category_code=code,
            defaults={"category_name": name},
        )


class Migration(migrations.Migration):
    dependencies = [("board", "0002_postmodel_deleted_at_commentmodel")]

    operations = [migrations.RunPython(create_notice_categories, migrations.RunPython.noop)]
