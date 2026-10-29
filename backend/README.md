# ERP Backend

The Django backend is managed with `uv`. See the repository root README for setup and run commands.

## Settings

- `config.settings.development` loads `.env.development` and is the `manage.py` default.
- `config.settings.production` loads `.env.production` and is the ASGI/WSGI default.
- `config.settings.test` uses an in-memory SQLite database.

Set `DEVELOPMENT_OFFLINE_MODE=true` in `.env.development` to start without PostgreSQL or Redis.
The health endpoint then reports the simulated outage and vacation endpoints return HTTP 503.

## Development database reuse

Run `uv sync` and restart the backend after dependency updates. Development PostgreSQL uses
`psycopg[binary,pool]`, with a process-wide pool shared by request threads. Defaults:
`DB_POOL_ENABLED=true`, `DB_POOL_MIN_SIZE=0`, `DB_POOL_MAX_SIZE=4`, `DB_POOL_TIMEOUT=15`,
`DB_CONNECT_TIMEOUT=10`. Connections return to the pool at request end (`CONN_MAX_AGE=0`), are checked
on checkout, and shrink after 60 seconds idle. Set `DB_POOL_ENABLED=false` to disable pooling.
SQLite tests/offline development do not use it. Production retains its existing WSGI persistent
connection settings. A working SSH tunnel is still required for remote development services.
Development Redis health checks default to `HEALTH_CHECK_TIMEOUT_SECONDS=10.0` per connect/read
operation to allow the SSH handshake. Update existing local values and restart to apply; production
settings retain their separate timeout. This does not set a total deadline for the health endpoint.
See the [performance report](../docs/reports/2026-10-29_database-query-improvements.md).

## Reference list cache

Department/position/role lists and active vacation types use a separate Django `reference` cache
alias. Production enables it by default; development requires `REFERENCE_CACHE_ENABLED=true`.
`REFERENCE_CACHE_URL` defaults to `REDIS_URL` and accepts `rediss://` for TLS Valkey.
Defaults: TTL 180 seconds (maximum 300), connect/read timeout 0.2 seconds each, no retries,
8 connections per process. Use a unique `REFERENCE_CACHE_KEY_PREFIX` per deployment.
Saves/deletes rotate the list generation after commit. Redis failures fall back to the DB and
suspend cache reads for 5 seconds. Direct SQL/bulk updates and failed invalidation can leave display
metadata stale until TTL. Balances, employee eligibility, permission checks and command type lookup
remain fresh DB reads; sessions are unchanged. Tests use only SQLite and local-memory caches.
See the [cache report](../docs/reports/2026-10-29_reference-cache.md).

## Vacation module

The `vacation` Django app follows the project's domain-module layout. Its `domain` and `application`
packages are framework-independent; Django ORM and temporary employee/balance adapters live under
`infrastructure`, while DRF endpoints live under `presentation`.

## Payroll module

The `payroll` Django app follows the same domain-module layout as `vacation` and `workforce`.
Statement creation, item entry, confirmation, confirmation-cancellation and reconfirmation all run
through `application/service.py` and are recorded to `PayrollHistory`. Only employees holding the
`PAYROLL_MANAGER` role (seeded by `workforce/migrations/0003_payroll_manager_role.py`) can create or
change statements; other employees can only read their own. The four core payroll tables are legacy tables registered through a state-only initial migration.
Public holidays and subsequent additions use ordinary migrations. An empty RDS database requires an
approved baseline schema before migrations; see the [deployment guide](../docs/guides/ec2-rds-deployment.md).

Run the fast test suite without a database connection:

```bash
uv run pytest -q
```

## Production containers

Use rootless Docker Compose with the backend and nginx image targets in deploy/Dockerfile.
See the [EC2/RDS deployment guide](../docs/guides/ec2-rds-deployment.md).
Production static files are collected during image build without secrets or database access;
nginx serves them alongside the frontend build. Migrations are never run at container startup.
