import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.postgresql.base import DatabaseWrapper

from config.settings.database import development_connection_options

POOL_KEYS = (
    "DB_POOL_ENABLED", "DB_POOL_MIN_SIZE", "DB_POOL_MAX_SIZE",
    "DB_POOL_TIMEOUT", "DB_CONNECT_TIMEOUT",
)


@pytest.fixture
def clean_pool_environment(monkeypatch):
    for key in POOL_KEYS:
        monkeypatch.delenv(key, raising=False)
    return environ.Env()


@pytest.mark.parametrize("offline,enabled", [(False, True), (False, False), (True, True)])
def test_development_settings_pool_and_offline_are_separate(offline: bool, enabled: bool) -> None:
    isolated_env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.development",
        "DJANGO_ENV_FILE": "/nonexistent/erp-test-env",
        "DEVELOPMENT_OFFLINE_MODE": str(offline),
        "DB_POOL_ENABLED": str(enabled),
        "DB_POOL_MIN_SIZE": "0",
        "DB_POOL_MAX_SIZE": "4",
        "DB_POOL_TIMEOUT": "2",
        "DB_CONNECT_TIMEOUT": "3",
    }
    result = subprocess.run(
        [sys.executable, "-c", """
import json
from django.conf import settings
config = settings.DATABASES['default']
print(json.dumps({'engine': config['ENGINE'], 'options': config.get('OPTIONS', {}),
                  'age': config.get('CONN_MAX_AGE', 0)}))
"""],
        cwd=Path(__file__).resolve().parent.parent,
        env=isolated_env, capture_output=True, text=True, check=True,
    )
    actual = json.loads(result.stdout)
    assert actual["age"] == 0
    if offline:
        assert actual["engine"] == "django.db.backends.sqlite3"
        assert actual["options"] == {}
    else:
        assert actual["engine"] == "django.db.backends.postgresql"
        assert actual["options"]["connect_timeout"] == 3
        assert ("pool" in actual["options"]) is enabled


@pytest.mark.parametrize("key,value", [
    ("DB_POOL_MIN_SIZE", "-1"), ("DB_POOL_MIN_SIZE", "5"),
    ("DB_POOL_MAX_SIZE", "0"), ("DB_POOL_TIMEOUT", "0"), ("DB_POOL_TIMEOUT", "nan"),
    ("DB_CONNECT_TIMEOUT", "0"),
])
def test_invalid_pool_bounds_fail_before_connecting(
    clean_pool_environment, monkeypatch, key, value,
):
    monkeypatch.setenv(key, value)
    with pytest.raises(ImproperlyConfigured):
        development_connection_options(clean_pool_environment)


def test_django_pool_is_shared_and_connections_return_without_closing(
    clean_pool_environment, monkeypatch,
):
    config = deepcopy(connections.databases["default"])
    config.update({
        "ENGINE": "django.db.backends.postgresql", "NAME": "unused",
        "CONN_MAX_AGE": 0, "CONN_HEALTH_CHECKS": True,
        "OPTIONS": development_connection_options(clean_pool_environment),
    })
    assert config["OPTIONS"]["connect_timeout"] == 10
    assert config["OPTIONS"]["pool"]["timeout"] > config["OPTIONS"]["connect_timeout"]
    assert config["OPTIONS"]["pool"]["reconnect_timeout"] == 30
    constructor = MagicMock()
    pool = constructor.return_value
    borrowed = MagicMock()
    borrowed._pool = pool
    pool.getconn.return_value = borrowed
    monkeypatch.setattr("psycopg_pool.ConnectionPool", constructor)
    first = DatabaseWrapper(config, alias="isolated-development-pool")
    second = DatabaseWrapper(config, alias=first.alias)
    try:
        assert first.pool is second.pool
        assert constructor.call_count == 1
        assert constructor.call_args.kwargs["open"] is False
        assert constructor.call_args.kwargs["max_size"] == 4
        assert constructor.call_args.kwargs["timeout"] == 15
        assert first.get_new_connection({}) is borrowed
        first.connection = borrowed
        first._close()
        pool.putconn.assert_called_once_with(borrowed)
        borrowed.close.assert_not_called()
        assert first.connection is None
        assert second.get_new_connection({}) is borrowed
    finally:
        DatabaseWrapper._connection_pools.pop(first.alias, None)
