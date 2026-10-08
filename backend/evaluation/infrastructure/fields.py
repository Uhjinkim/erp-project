from datetime import UTC

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampField(models.DateTimeField):
    """A DateTimeField stored as PostgreSQL `timestamp` (without time zone).

    Django's DateTimeField becomes `timestamptz` on PostgreSQL, while the ERP tables use
    `timestamp`. Values are written as UTC wall time and read back as aware UTC datetimes,
    so application code sees the same values as with a regular DateTimeField.
    """

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return "timestamp"
        return super().db_type(connection)

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if (
            connection.vendor == "postgresql"
            and value is not None
            and timezone.is_aware(value)
        ):
            return timezone.make_naive(value, UTC)
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None and settings.USE_TZ and timezone.is_naive(value):
            return timezone.make_aware(value, UTC)
        return value
