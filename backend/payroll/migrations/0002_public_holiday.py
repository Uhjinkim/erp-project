# Genuinely new table; no legacy equivalent exists for settlement-date holiday adjustment.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payroll", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="PublicHolidayModel",
            fields=[
                ("holiday_date", models.DateField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "db_table": "payroll_public_holidays",
                "ordering": ["holiday_date"],
            },
        ),
    ]
