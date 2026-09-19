from config.settings.development import *  # noqa: F403

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/private/tmp/erp-project-vacation-demo.sqlite3",
    }
}
