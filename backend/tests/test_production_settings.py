"""Production config must validate without connecting to shared services."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_production_proxy_and_rds_settings(tmp_path):
    production_env = {
        **os.environ,
        "DJANGO_ENV_FILE": str(tmp_path / "absent.env"),
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "test-only-production-config-key-" * 3,
        "DJANGO_ALLOWED_HOSTS": "erp.example.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://erp.example.com",
        "DB_NAME": "unused",
        "DB_USER": "unused",
        "DB_PASSWORD": "unused",
        "DB_HOST": "unused.invalid",
        "DB_SSLMODE": "verify-full",
        "DB_SSLROOTCERT": "/unused/rds-ca.pem",
        "REDIS_URL": "redis://unused.invalid:6379/0",
    }
    code = """
import json
import django
from django.conf import settings
from django.test import Client

django.setup()
# CSRF bootstrap exercises SecurityMiddleware without any DB/Redis calls.
client = Client()
plain = client.get('/api/auth/csrf/', HTTP_HOST='erp.example.com')
secure = client.get('/api/auth/csrf/', HTTP_HOST='erp.example.com',
                    HTTP_X_FORWARDED_PROTO='https')
print(json.dumps({
    'redirect': plain.status_code,
    'secure': secure.status_code,
    'csrf_secure': bool(secure.cookies['csrftoken']['secure']),
    'hsts': secure.headers.get('Strict-Transport-Security'),
    'ssl': settings.DATABASES['default']['OPTIONS']['sslmode'],
    'ca': settings.DATABASES['default']['OPTIONS']['sslrootcert'],
    'offline': settings.DEVELOPMENT_OFFLINE_MODE,
    'integration': settings.VACATION_INTEGRATION_MODE,
    'static': str(settings.STATIC_ROOT),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parent.parent,
        env=production_env,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = json.loads(result.stdout)
    assert actual["redirect"] == 301
    assert actual["secure"] == 200
    assert actual["csrf_secure"] is True
    assert actual["hsts"] == "max-age=3600"
    assert actual["ssl"] == "verify-full"
    assert actual["ca"] == "/unused/rds-ca.pem"
    assert actual["offline"] is False
    assert actual["integration"] == "database"
    assert actual["static"].endswith("/backend/staticfiles")
