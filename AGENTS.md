# AGENTS.md

## Project overview

This repository contains an ERP application with two independently managed parts:

- `backend/`: Python 3.13, Django 5.2 LTS, and `uv`
- `frontend/`: React 19, TypeScript, Vite, and Bun 1.4

PostgreSQL and Redis run on team-managed remote infrastructure. Local applications reach them through SSH local forwarding; there is no local container workflow in this repository.

## Repository layout

- `backend/config/`: Django project settings, URLs, ASGI, and WSGI configuration
- `backend/<module>/`: bounded-context Django apps such as `vacation` and `workforce`
- `frontend/src/`: React application source and styles
- `nginx/`: local development reverse-proxy configuration templates
- `docs/specs/notion/`: repository snapshots and implementation mappings for Notion specs
- `docs/reports/`: dated implementation and validation reports
- `scripts/`: cross-platform development helpers, including SSH tunnel scripts
- `.env.example`: documented environment-variable template
- `README.md`: canonical developer setup and infrastructure instructions

Keep backend and frontend dependencies within their respective directories and lockfiles. Do not add generated environments or build output to version control.

## Setup and development

Copy `.env.example` to `.env` and use credentials supplied by the infrastructure administrator. Never commit `.env` or store an SSH password in files, scripts, or command arguments.

The standard SSH forwarding ports are:

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Run the backend from `backend/`:

```bash
uv sync
uv run python manage.py runserver
```

Run the frontend from `frontend/`:

```bash
bun install --frozen-lockfile
bun run dev
```

The frontend runs at `http://localhost:5173`; Vite proxies `/api` to Django at `http://localhost:8000`.

After opening the SSH tunnel, macOS/Linux developers can run Django, Vite, and nginx together:

```bash
./scripts/start-dev.sh
```

The nginx development entry point is `http://localhost:8080`. Check the local prerequisites and generated
nginx configuration without starting services with `./scripts/start-dev.sh --check`. Windows uses
`.\scripts\start-dev.ps1` and `.\scripts\start-dev.ps1 -Check`.

## Validation

Run checks relevant to every changed area before finishing.

Backend checks, from `backend/`:

```bash
uv run python manage.py check
uv run ruff check .
uv run pytest
uv run python manage.py makemigrations --check --dry-run
```

Frontend checks, from `frontend/`:

```bash
bun run lint
bun run build
```

Development proxy checks, from the repository root:

```bash
bash -n scripts/start-dev.sh
./scripts/start-dev.sh --check
```

When adding tests, run the narrowest applicable tests during development and the complete affected suite before finishing. Add regression coverage for bug fixes when practical.

## Backend conventions

- Follow Django conventions and keep domain functionality in focused Django apps rather than expanding `config/` with business logic.
- Treat each business app as a bounded context. Prefer `domain/`, `application/`, `infrastructure/`, and `presentation/` packages inside the app, following the established `vacation/` example.
- Keep `domain/` pure Python: no Django, DRF, ORM, environment, or network imports.
- Keep use cases in `application/`; depend on Protocol/ABC ports rather than concrete ORM adapters.
- Put Django ORM, external-service adapters, and repository implementations in `infrastructure/`. Presentation code may assemble concrete dependencies but must not contain business rules.
- Keep serializers responsible for transport-shape validation. Put business invariants and state transitions in domain policies/entities or application use cases.
- Use Django migrations for all schema changes. Commit migration files with the model changes that require them.
- Generate migrations with `uv run python manage.py makemigrations`.
- Do not run `migrate`, destructive management commands, data fixes, or ad hoc writes against the shared database unless the user explicitly authorizes it and confirms the target environment and permissions.
- Preserve the existing Ruff configuration: Python 3.13, 100-character line length, and enabled `E`, `F`, `I`, and `UP` rules.
- Read configuration and secrets from environment variables. If a variable is added, document it in `.env.example` and the root README when setup behavior changes.
- Keep API endpoints under `/api/` and preserve trailing-slash conventions.

## Product specifications and traceability

- The Notion `ERP 프로젝트` workspace is the upstream product-design source. Relevant pages include the DDD/clean-architecture strategy, business rules, feature specs, detailed specs, table decisions, and table definitions.
- Before changing a business rule, read the relevant Notion source and the matching snapshot in `docs/specs/notion/`. If they differ, treat Notion as upstream and update the repository document in the same change.
- Do not silently invent a decision for an item marked unresolved in Notion. Record the open question and request a product decision when it affects behavior or schema.
- Preserve traceability identifiers such as `HR-###`, `LV-###`, and `FN-HR-###` in tests, docstrings, or implementation-mapping documents where practical.
- Repository Markdown is an implementation-oriented snapshot, not a replacement for Notion. Include the source page URL and last verified date in each snapshot.

## Shared infrastructure and data safety

- PostgreSQL and Redis are shared remote services reached through SSH forwarding. A successful localhost connection does not mean the service is disposable.
- Default to SQLite, fakes, and mocks for automated tests. Do not make test success depend on an open SSH tunnel.
- Schema inspection against shared PostgreSQL must be read-only. Never run migrations, create users, seed data, flush Redis, or execute ad hoc writes without explicit authorization and confirmed environment details.
- Legacy ERP tables use state-only migrations where documented. Compare Django model state, generated SQL, and the actual PostgreSQL schema before planning any deployment migration.
- Do not expose `.env` content, credentials, employee personal data, payroll data, or account numbers in logs, reports, fixtures, screenshots, or tool output.

## Frontend conventions

- Use TypeScript and React function components with hooks.
- Keep strict TypeScript checks passing; avoid `any` unless an integration makes it unavoidable and the reason is documented.
- Follow the existing formatting style: two-space indentation, double quotes, and no semicolons.
- Keep API calls relative (for example, `/api/health/`) so the Vite proxy and same-origin deployments continue to work.
- Prefer component-local organization as the application grows; extract shared components, hooks, and utilities only when they have clear reuse or simplify complex code.
- Maintain accessible HTML: semantic elements, associated labels, keyboard operability, and visible focus states.

## Dependency and generated-file policy

- Use `uv` for Python dependencies and update both `backend/pyproject.toml` and `backend/uv.lock`.
- Use Bun for frontend dependencies and update both `frontend/package.json` and `frontend/bun.lock`.
- Do not hand-edit lockfiles.
- Do not commit `.venv/`, `node_modules/`, `frontend/dist/`, caches, credentials, database dumps, or other machine-generated artifacts.
- Avoid introducing Docker or Podman requirements for local development unless the project architecture is intentionally changed and the documentation is updated with it.

## Change discipline

- Inspect nearby code and documentation before editing; preserve established behavior unless the task requires changing it.
- Keep changes scoped to the request and avoid unrelated refactors.
- Update documentation when commands, configuration, ports, dependencies, or developer workflow change.
- Do not overwrite unrelated user changes in a dirty working tree.
- Treat the remote database and Redis instance as shared resources. Prefer read-only diagnostics and mocks/fakes for tests; never flush or reseed shared services without explicit authorization.
