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


def test_timestamp_field_stores_utc_wall_time_and_reads_back_aware() -> None:
    field = TimestampField()
    aware = datetime(2026, 10, 8, 9, 30, tzinfo=UTC)

    stored = field.get_db_prep_value(aware, POSTGRES, prepared=True)
    assert stored == datetime(2026, 10, 8, 9, 30)
    assert stored.tzinfo is None

    assert field.from_db_value(stored, None, POSTGRES) == aware
