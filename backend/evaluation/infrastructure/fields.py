from datetime import UTC

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimestampField(models.DateTimeField):
    """A DateTimeField stored as PostgreSQL `timestamp` (without time zone).

    Django's DateTimeField becomes `timestamptz` on PostgreSQL, while the ERP tables use
    `timestamp`. Aware values are sent unchanged, so PostgreSQL stores them as UTC wall time
    in Django's UTC session, like the other ERP `timestamp` columns. Stripping the time zone
    in Python instead let the driver read the naive value as local time (a 9-hour shift).
    Values read back are made aware as UTC.
    """

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return "timestamp"
        return super().db_type(connection)

    def from_db_value(self, value, expression, connection):
        if value is not None and settings.USE_TZ and timezone.is_naive(value):
            return timezone.make_aware(value, UTC)
        return value
