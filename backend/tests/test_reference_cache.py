"""Reference-list caching never replaces HR/LV authorization or transactional state."""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.cache import caches
from django.db import transaction
from redis.exceptions import TimeoutError
from rest_framework.test import APIClient

from accounts.models import User
from shared.infrastructure import reference_cache
from vacation.infrastructure.models import LeaveTypeModel
from vacation.infrastructure.repositories import DjangoVacationTypeRepository
from workforce.infrastructure.models import Department, Position, Role


@pytest.fixture
def cached(settings, monkeypatch):
    settings.REFERENCE_CACHE_ENABLED = True
    settings.REFERENCE_CACHE_TTL = 180
    monkeypatch.setattr(reference_cache, "_unavailable_until", 0)
    cache = caches["reference"]
    assert cache.__class__.__name__ == "LocMemCache"  # Never clear the shared Redis.
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def client(db):
    viewer = User.objects.create_user(email="cache@example.test", is_superuser=True)
    client = APIClient()
    client.force_authenticate(viewer)
    return client


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("model", "values", "endpoint"),
    [
        (Department, {"dept_no": 10, "dept_name": "합성 부서"}, "departments"),
        (Position, {"position_code": "STAFF", "position_name": "사원"}, "positions"),
        (Role, {"role_code": "HR_MANAGER", "role_name": "인사관리자"}, "roles"),
    ],
)
def test_repeated_master_lists_skip_db_and_keep_permissions(
    cached, client, django_assert_num_queries, model, values, endpoint
):
    model.objects.create(**values)
    url = f"/api/workforce/{endpoint}/"
    with django_assert_num_queries(1):
        first = client.get(url)
    assert first.status_code == 200
    with django_assert_num_queries(0):
        second = client.get(url)
    assert second.json() == first.json()
    assert APIClient().get(url).status_code == 403
    with django_assert_num_queries(1):
        assert client.get(url + "?unused=1").json() == first.json()


@pytest.mark.django_db(transaction=True)
def test_api_write_invalidates_and_denies_non_hr(cached, client):
    position = Position.objects.create(position_code="STAFF", position_name="사원")
    url = "/api/workforce/positions/"
    assert client.get(url).json()[0]["position_name"] == "사원"
    response = client.patch(url + position.pk + "/", {"position_name": "대리"}, format="json")
    assert response.status_code == 200
    assert client.get(url).json()[0]["position_name"] == "대리"
    member = User.objects.create_user(email="member-cache@example.test")
    client.force_authenticate(member)
    assert client.get(url).status_code == 200
    assert client.patch(url + position.pk + "/", {"position_name": "과장"}).status_code == 403
    assert client.get(url).json()[0]["position_name"] == "대리"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("model", "values", "resource"),
    [
        (Department, {"dept_no": 10, "dept_name": "합성 부서"}, "workforce:departments"),
        (Position, {"position_code": "STAFF", "position_name": "사원"}, "workforce:positions"),
        (Role, {"role_code": "HR_MANAGER", "role_name": "인사관리자"}, "workforce:roles"),
        (LeaveTypeModel, {"type_id": "ANNUAL", "type_name": "연차"}, "vacation:types"),
    ],
)
def test_save_delete_invalidate_including_non_api_paths(cached, model, values, resource):
    def load():
        return list(model.objects.values_list(model._meta.pk.name, flat=True))

    assert reference_cache.reference_list(resource, load) == []
    row = model.objects.create(**values)
    assert reference_cache.reference_list(resource, load) == [row.pk]
    row.delete()
    assert reference_cache.reference_list(resource, load) == []


@pytest.mark.django_db(transaction=True)
def test_rollback_neither_invalidates_payload_nor_publishes_new_rows(cached):
    Position.objects.create(position_code="STAFF", position_name="사원")
    load = Mock(return_value=["STAFF"])
    assert reference_cache.reference_list("workforce:positions", load) == ["STAFF"]
    with pytest.raises(RuntimeError), transaction.atomic():
        Position.objects.create(position_code="TEMP", position_name="임시")
        raise RuntimeError("rollback")
    assert reference_cache.reference_list("workforce:positions", load) == ["STAFF"]
    assert load.call_count == 1
    with pytest.raises(RuntimeError), transaction.atomic():
        reference_cache.reference_list("new-resource", lambda: ["uncommitted"])
        raise RuntimeError("rollback")
    assert reference_cache.reference_list("new-resource", lambda: []) == []


@pytest.mark.django_db(transaction=True)
def test_invalidation_during_fill_cannot_restore_old_generation(cached):
    def old_load():
        reference_cache.invalidate_reference("race")
        return ["old"]

    assert reference_cache.reference_list("race", old_load) == ["old"]
    assert reference_cache.reference_list("race", lambda: ["new"]) == ["new"]


@pytest.mark.django_db(transaction=True)
def test_read_failure_falls_back_and_skips_cache_temporarily(cached, caplog):
    loader = Mock(return_value=["db"])
    with patch.object(cached, "get", side_effect=TimeoutError("sensitive-url")) as get:
        assert reference_cache.reference_list("fail", loader) == ["db"]
        assert reference_cache.reference_list("fail", loader) == ["db"]
    assert get.call_count == 1
    assert loader.call_count == 2
    assert "sensitive-url" not in caplog.text


@pytest.mark.django_db(transaction=True)
def test_write_failure_does_not_break_successful_db_read(cached):
    with patch.object(cached, "set", side_effect=TimeoutError("unavailable")):
        assert reference_cache.reference_list("write-fail", lambda: ["db"]) == ["db"]


@pytest.mark.django_db(transaction=True)
def test_vacation_list_cached_but_command_type_get_is_fresh(cached, django_assert_num_queries):
    kind = LeaveTypeModel.objects.create(
        type_id="ANNUAL", type_name="연차", deduct_days=Decimal("1.00")
    )
    repo = DjangoVacationTypeRepository()
    with django_assert_num_queries(1):
        assert repo.list_active()[0].deduct_days == Decimal("1.00")
    with django_assert_num_queries(0):
        assert repo.list_active()[0].deduct_days == Decimal("1.00")
    # External/bulk writes skip signals: command reads must still see them immediately.
    LeaveTypeModel.objects.filter(pk=kind.pk).update(deduct_days=Decimal("0.50"))
    with django_assert_num_queries(1):
        assert repo.get("ANNUAL").deduct_days == Decimal("0.50")
    assert repo.list_active()[0].deduct_days == Decimal("1.00")
    kind.refresh_from_db()
    kind.save()
    assert repo.list_active()[0].deduct_days == Decimal("0.50")


@pytest.mark.django_db(transaction=True)
def test_expired_or_evicted_payload_reloads_db(cached):
    loader = Mock(side_effect=[["old"], ["new"]])
    assert reference_cache.reference_list("expiry", loader) == ["old"]
    generation = cached.get("expiry:generation")
    cached.delete(f"expiry:{generation}")
    assert reference_cache.reference_list("expiry", loader) == ["new"]


@pytest.mark.django_db(transaction=True)
def test_db_loader_errors_are_not_hidden_or_cached(cached):
    loader = Mock(side_effect=ValueError("database failure"))
    with pytest.raises(ValueError, match="database failure"):
        reference_cache.reference_list("loader-fail", loader)
    assert loader.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_cached_type_api_always_refreshes_each_employees_balance(cached, settings):
    from datetime import date

    from vacation.infrastructure.models import LeaveBalanceModel
    from workforce.infrastructure.models import Employee, Person

    settings.VACATION_INTEGRATION_MODE = "database"
    position = Position.objects.create(position_code="STAFF", position_name="사원")
    annual = LeaveTypeModel.objects.create(type_id="ANNUAL", type_name="연차", deduct_days=1)
    LeaveTypeModel.objects.create(type_id="HALF", type_name="반차", deduct_days=Decimal("0.50"))
    clients = []
    balances = []
    for number, remaining in [(1001, 3), (1002, 7)]:
        employee = Employee.objects.create(
            employee_no=number, person=Person.objects.create(name=f"합성 {number}"),
            position=position, tenure_status="재직", hire_date=date(2024, 1, 1),
        )
        viewer = User.objects.create_user(email=f"cache{number}@example.test", employee=employee)
        client = APIClient()
        client.force_authenticate(viewer)
        clients.append(client)
        balances.append(LeaveBalanceModel.objects.create(
            employee=employee, vacation_type=annual, remaining_days=remaining
        ))
    url = "/api/vacations/types/?include_balance=true"

    def remaining(client):
        response = client.get(url)
        assert response.status_code == 200
        return {row["type_id"]: Decimal(row["remaining_days"]) for row in response.json()}

    assert remaining(clients[0]) == {"ANNUAL": 3, "HALF": 3}
    assert remaining(clients[1]) == {"ANNUAL": 7, "HALF": 7}
    LeaveBalanceModel.objects.filter(pk=balances[0].pk).update(remaining_days=Decimal("2.50"))
    assert remaining(clients[0]) == {"ANNUAL": Decimal("2.50"), "HALF": Decimal("2.50")}
    assert remaining(clients[1]) == {"ANNUAL": 7, "HALF": 7}
    # Warming the list must not allow an inactive employee to bypass application checks.
    employee = clients[0].handler._force_user.employee
    Employee.objects.filter(pk=employee.pk).update(tenure_status="퇴사")
    response = clients[0].get(url)
    assert response.status_code == 400
    assert response.json()["code"] == "inactive_employee"


def test_cache_settings_bound_wait_and_separate_environment_namespaces():
    import environ
    from django.core.exceptions import ImproperlyConfigured

    from config.settings.reference_cache import reference_cache_settings

    with patch.dict("os.environ", {}, clear=True):
        env = environ.Env()
        production = reference_cache_settings(env, "rediss://cache.invalid:6379/0", "production")
        development = reference_cache_settings(env, "redis://cache.invalid:6379/0", "development")
    assert production["REFERENCE_CACHE_ENABLED"] is True
    assert development["REFERENCE_CACHE_ENABLED"] is False
    assert production["CACHES"]["reference"]["KEY_PREFIX"] != (
        development["CACHES"]["reference"]["KEY_PREFIX"]
    )
    options = production["CACHES"]["reference"]["OPTIONS"]
    assert options["retry"].get_retries() == 0
    assert options["socket_timeout"] == options["socket_connect_timeout"] == 0.2
    for key, value in [("REFERENCE_CACHE_TTL", "0"), ("REFERENCE_CACHE_TIMEOUT", "nan")]:
        with patch.dict("os.environ", {key: value}, clear=True):
            with pytest.raises(ImproperlyConfigured):
                reference_cache_settings(
                    environ.Env(), "redis://cache.invalid:6379/0", "production"
                )
