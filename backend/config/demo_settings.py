import tempfile
from pathlib import Path

from config.settings.development import *  # noqa: F403

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(tempfile.gettempdir()) / "erp-project-demo.sqlite3"),
    }
}

# Legacy-table migrations are state-only against the real shared PostgreSQL schema, so they
# do not create tables. Fall back to Django's model state for a from-scratch local SQLite demo.
MIGRATION_MODULES = {
    "accounts": None,
    "vacation": None,
    "workforce": None,
}
