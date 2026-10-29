# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.29@sha256:eb2843a1e56fd9e30c7276ce1a52cba86e64c7b385f5e3279a0e08e02dd058fc AS uv
FROM oven/bun:1.4.0@sha256:5ff609364c049b54eb0ff560ec96319729a972078ef2c755d758f0c6ef89c2d6 AS bun

FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS python-build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
# Static collection needs neither deployment secrets nor a database connection.
RUN .venv/bin/python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings.test'; import django; django.setup(); from django.conf import settings; settings.STATIC_ROOT='/app/backend/staticfiles'; from django.core.management import call_command; call_command('collectstatic', interactive=False)"

FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH=/app/backend/.venv/bin:$PATH
WORKDIR /app/backend
COPY --from=python-build /app/backend /app/backend
USER 10001:10001
EXPOSE 8000
# No published backend port; only nginx may connect on the Compose network.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--forwarded-allow-ips=*", "--error-logfile", "-"]

FROM node:24-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c AS frontend-build
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
ENV VITE_APP_ENV=production VITE_AUTH_MODE=session VITE_API_BASE_URL=""
RUN bun run build

FROM nginxinc/nginx-unprivileged:1.28-alpine@sha256:7377697a821c131a924a7105fafbe7414db4e9fcc77a6f08f776f33f141ec3f8 AS nginx
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY --from=python-build /app/backend/staticfiles /usr/share/nginx/static
COPY deploy/nginx/nginx.conf.template /etc/nginx/erp.conf.template
COPY deploy/nginx/start.sh /usr/local/bin/erp-nginx
USER 101:101
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "/usr/local/bin/erp-nginx"]
