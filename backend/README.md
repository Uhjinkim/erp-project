# ERP Backend

The Django backend is managed with `uv`. See the repository root README for setup and run commands.

## Vacation module

The `vacation` Django app follows the project's domain-module layout. Its `domain` and `application`
packages are framework-independent; Django ORM and temporary employee/balance adapters live under
`infrastructure`, while DRF endpoints live under `presentation`.

Run its fast tests without a database connection:

```bash
uv run pytest -q
```
