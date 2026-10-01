# AGENTS.md

## Project overview

This repository contains an ERP application with two independently managed parts:

- `backend/`: Python 3.13, Django 5.2 LTS, and `uv`
- `frontend/`: React 19, TypeScript, Vite, and Bun 1.4

PostgreSQL and Redis run on team-managed remote infrastructure. Local applications reach them through SSH local forwarding; there is no local container workflow in this repository.

## Instruction authority and agent compatibility

- This file is the canonical repository instruction set for Codex, Claude, and other coding agents.
- Agent-specific entry files may point to this file but must not duplicate or redefine its rules. If instructions conflict, the user's current request and the nearest applicable `AGENTS.md` take precedence.
- Before editing, read this file, inspect the working tree, and read the implementation and documentation nearest to the target module.
- For feature-branch work, also read `docs/guides/module-branch-docs-workflow.md` and the current branch's file under `docs/contributions/` when one exists.
- Do not assume another agent has preserved context. Record durable decisions, validation results, open questions, and documentation impacts in the repository paths defined below.

## Repository layout

- `backend/config/`: Django project settings, URLs, ASGI, and WSGI configuration
- `backend/<module>/`: bounded-context Django apps such as `vacation` and `workforce`
- `frontend/src/`: React application source and styles
- `nginx/`: local development reverse-proxy configuration templates
- `docs/specs/notion/`: repository snapshots and implementation mappings for Notion specs
- `docs/reports/`: dated implementation and validation reports
- `docs/guides/`: shared development and collaboration workflows
- `docs/contributions/<module>/<branch-slug>/`: feature-branch design and documentation proposals
- `scripts/`: cross-platform development helpers, including SSH tunnel, integrated startup, and documentation workflow scripts
- `.env.example`: documented environment-variable template
- `README.md`: canonical developer setup and infrastructure instructions

Keep backend and frontend dependencies within their respective directories and lockfiles. Do not add generated environments or build output to version control.

## Setup and development

Copy `.env.example` to `.env` and use credentials supplied by the infrastructure administrator. Never commit `.env` or store an SSH password in files, scripts, or command arguments.

The standard SSH forwarding ports are:

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

After opening the SSH tunnel, use the integrated development entry point by default.

macOS/Linux:

```bash
./scripts/start-dev.sh
```

Windows PowerShell:

```powershell
.\scripts\start-dev.ps1
```

The nginx development entry point is `http://localhost:8080`. Check prerequisites and the generated nginx configuration without starting services with `./scripts/start-dev.sh --check` or `.\scripts\start-dev.ps1 -Check`.

Run components individually only for focused development or troubleshooting.

Backend, from `backend/`:

```bash
uv sync
uv run python manage.py runserver
```

Frontend, from `frontend/`:

```bash
bun install --frozen-lockfile
bun run dev
```

The frontend runs at `http://localhost:5173`; Vite proxies `/api` to Django at `http://localhost:8000`.

Install nginx on Windows with `winget install nginxinc.nginx`, then open a new PowerShell session. The Windows startup script creates and removes its per-run nginx log and temporary directories.

## Branch and documentation workflow

- Use `dev` as the integration branch and `main` as the release branch. Create feature branches from the latest `dev`, normally as `feature/<module>-<topic>`.
- Prefer merging `origin/dev` into shared feature branches. Do not rewrite a branch used by other team members with rebase or force push.
- A feature branch owns its module code, tests, migrations, and `docs/contributions/<module>/<branch-slug>/README.md`.
- Feature branches must not directly edit canonical documentation: root `README.md`, `docs/specs/`, `docs/reports/`, `docs/guides/`, or `docs/contributions/README.md`, unless the user or documentation owner explicitly assigns canonical-document maintenance.
- Create a contribution draft with `./scripts/docs-workflow.sh init <module>` or `.\scripts\docs-workflow.ps1 init <module>`.
- Regularly merge `origin/dev` to detect code integration issues. When only current canonical documentation is needed, use `docs-workflow.sh sync` or `docs-workflow.ps1 sync`, review the diff, and commit the synchronized snapshot.
- Before a feature Pull Request, fetch `origin/dev`, commit the current work, and run `docs-workflow.sh check` or `docs-workflow.ps1 check`. This check is for feature branches; canonical documentation work on `dev` is expected to differ.
- After the feature is merged, the documentation owner reviews the contribution draft, updates Notion and canonical repository documents, and removes the integrated draft in a later `dev` commit.
- Never resolve documentation conflicts by discarding one side wholesale. Preserve both proposals in the contribution draft and let the documentation owner integrate the canonical wording.

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
bash -n scripts/docs-workflow.sh
```

On Windows, run `.\scripts\start-dev.ps1 -Check`. For documentation workflow changes, test the equivalent `init`, `sync`, and `check` paths on the operating systems affected by the change.

When adding tests, run the narrowest applicable tests during development and the complete affected suite before finishing. Add regression coverage for bug fixes when practical.

## Backend conventions

- Follow Django conventions and keep domain functionality in focused Django apps rather than expanding `config/` with business logic.
- Treat each business app as a bounded context. Prefer `domain/`, `application/`, `infrastructure/`, and `presentation/` packages inside the app, following the established `vacation/` example.
- New backend business modules should use the same four-layer structure. Do not introduce a competing module layout without an explicit architecture decision and documentation update.
- Keep `domain/` pure Python: no Django, DRF, ORM, environment, or network imports.
- Keep use cases in `application/`; depend on Protocol/ABC ports rather than concrete ORM adapters.
- Put Django ORM, external-service adapters, and repository implementations in `infrastructure/`. Presentation code may assemble concrete dependencies but must not contain business rules.
- Cross-context access must go through an application port and an infrastructure gateway. Do not import another context's ORM models into `domain/` or use them as hidden business dependencies in `application/`.
- Put transaction boundaries in application-facing units of work or infrastructure adapters. Do not spread partial multi-model writes across views, serializers, signals, or frontend calls.
- Keep serializers responsible for transport-shape validation. Put business invariants and state transitions in domain policies/entities or application use cases.
- Keep views thin: authenticate, authorize, validate transport input, assemble dependencies, invoke one use case, and map the result to an HTTP response.
- Treat signals as integration glue only. Do not hide primary commands or state transitions in signals.
- Use Django migrations for all schema changes. Commit migration files with the model changes that require them.
- Generate migrations with `uv run python manage.py makemigrations`.
- Do not run `migrate`, destructive management commands, data fixes, or ad hoc writes against the shared database unless the user explicitly authorizes it and confirms the target environment and permissions.
- Preserve the existing Ruff configuration: Python 3.13, 100-character line length, and enabled `E`, `F`, `I`, and `UP` rules.
- Read configuration and secrets from environment variables. If a variable is added, document it in `.env.example` and the root README when setup behavior changes.
- Keep API endpoints under `/api/` and preserve trailing-slash conventions.
- When an endpoint changes, add or update permission, validation, success, and failure coverage and record the documentation impact in the branch contribution draft.

### Backend module implementation sequence

Use this order for new or substantially changed bounded contexts:

1. Confirm relevant rule and feature IDs and record unresolved decisions.
2. Implement pure domain entities, value objects, policies, and exceptions.
3. Define application DTOs, commands, ports, and use cases against abstractions.
4. Implement ORM models, repositories, gateways, and units of work in infrastructure.
5. Add serializers, permissions, views, and URLs in presentation.
6. Add domain and application tests first, then infrastructure and API regression coverage.
7. Generate required migrations, inspect them, and run the migration drift check without applying them to shared services.
8. Update the feature contribution document with API, schema, configuration, validation, and canonical-document impacts.

## Product specifications and traceability

- The Notion `ERP 프로젝트` workspace is the upstream product-design source. Relevant pages include the DDD/clean-architecture strategy, business rules, feature specs, detailed specs, table decisions, and table definitions.
- Notion write access is limited to the designated documentation owner. Agents and team members without access must use the repository snapshots, record proposed changes in the branch contribution document, and must not pretend that Notion was verified or updated.
- Before changing a business rule, read the relevant Notion source when access is available and the matching snapshot in `docs/specs/notion/`. If they differ, treat Notion as upstream and route the canonical update through the documentation owner.
- Do not silently invent a decision for an item marked unresolved in Notion. Record the open question and request a product decision when it affects behavior or schema.
- Preserve traceability identifiers such as `HR-###`, `LV-###`, and `FN-HR-###` in tests, docstrings, or implementation-mapping documents where practical.
- Repository Markdown is an implementation-oriented snapshot, not a replacement for Notion. Include the source page URL and last verified date in each snapshot.
- `06-api-specification.md` is the current implemented API reference, `07-table-design-decisions.md` records table design decisions, and `08-table-specification.md` is the implementation-oriented table reference. Feature branches propose changes; the documentation owner updates these canonical files after review.

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
- Keep transport clients in `frontend/src/api/`, shared transport types in `frontend/src/types/`, and current reusable UI in `frontend/src/components/`. When a module becomes complex, group its internal UI, hooks, and state by feature without moving unrelated modules.
- Do not duplicate backend authorization or state-transition rules as authoritative frontend logic. The frontend may guide the user, but the backend remains responsible for enforcing business invariants.
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
- On a feature branch, write those documentation impacts to the contribution draft instead of editing canonical files directly. On authorized canonical-document work, update the relevant guide, specification, index, and dated report together.
- Do not overwrite unrelated user changes in a dirty working tree.
- Treat the remote database and Redis instance as shared resources. Prefer read-only diagnostics and mocks/fakes for tests; never flush or reseed shared services without explicit authorization.

## Agent completion checklist

Before handing work back, every coding agent must:

1. Confirm the change stays within the assigned bounded context and does not introduce forbidden inward dependencies.
2. Review `git diff` and `git status` and preserve unrelated user or agent changes.
3. Run the narrowest relevant tests, then the affected validation suite from this file.
4. Run `makemigrations --check --dry-run` for backend model work and never apply migrations to shared infrastructure without authorization.
5. For feature-branch work, update the current branch contribution draft with decisions, API/schema/configuration impacts, tests, and open questions.
6. On feature branches, run the documentation scope check against the latest `origin/dev`.
7. Report validations that were run, validations that could not run, shared-infrastructure actions, and remaining risks.
