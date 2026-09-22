# ERP Backend

The Django backend is managed with `uv`. See the repository root README for setup and run commands.

## Settings

- `config.settings.development` loads `.env.development` and is the `manage.py` default.
- `config.settings.production` loads `.env.production` and is the ASGI/WSGI default.
- `config.settings.test` uses an in-memory SQLite database.

Set `DEVELOPMENT_OFFLINE_MODE=true` in `.env.development` to start without PostgreSQL or Redis.
The health endpoint then reports the simulated outage and vacation endpoints return HTTP 503.

## Vacation module

The `vacation` Django app follows the project's domain-module layout. Its `domain` and `application`
packages are framework-independent; Django ORM and temporary employee/balance adapters live under
`infrastructure`, while DRF endpoints live under `presentation`.

## Payroll module

The `payroll` Django app follows the same domain-module layout as `vacation` and `workforce`.
Statement creation, item entry, confirmation, confirmation-cancellation and reconfirmation all run
through `application/service.py` and are recorded to `PayrollHistory`. Only employees holding the
`PAYROLL_MANAGER` role (seeded by `workforce/migrations/0003_payroll_manager_role.py`) can create or
change statements; other employees can only read their own. `payroll` has no legacy table in the
shared PostgreSQL database, so its migrations are ordinary `makemigrations` output rather than the
state-only migrations used for `workforce`/`vacation`.

Run the fast test suite without a database connection:

```bash
uv run pytest -q
```
