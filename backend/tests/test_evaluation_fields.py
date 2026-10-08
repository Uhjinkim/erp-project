from datetime import UTC, datetime
from types import SimpleNamespace

from django.db.backends.postgresql.operations import DatabaseOperations

from evaluation.infrastructure.fields import TimestampField
from evaluation.infrastructure.models import EvaluationHistoryModel

POSTGRES = SimpleNamespace(vendor="postgresql", ops=DatabaseOperations(None))


def test_history_changed_at_is_timestamp_without_time_zone_on_postgresql() -> None:
    field = EvaluationHistoryModel._meta.get_field("changed_at")
    assert isinstance(field, TimestampField)
    assert field.db_type(POSTGRES) == "timestamp"


def test_timestamp_field_sends_aware_values_and_reads_back_utc() -> None:
    field = TimestampField()
    aware = datetime(2026, 10, 8, 9, 30, tzinfo=UTC)

    # Sent aware: a naive value would be read by the driver as local time (9-hour shift).
    assert field.get_db_prep_value(aware, POSTGRES, prepared=True) == aware

    # A `timestamp` column returns UTC wall time without tzinfo.
    assert field.from_db_value(aware.replace(tzinfo=None), None, POSTGRES) == aware
