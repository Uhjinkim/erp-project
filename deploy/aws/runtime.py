#!/usr/bin/env python3
"""Run Compose with memory-only Secrets Manager values, under the erp user."""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path("/etc/erp/runtime.json")
SECRET_KEYS = {
    "DJANGO_SECRET_KEY",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "REDIS_URL",
    "REFERENCE_CACHE_URL",
}
REQUIRED_KEYS = {"DJANGO_SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD"}


def environment(config, secret):
    """Accept only documented keys; deployment transport settings stay authoritative."""
    if not isinstance(secret, dict):
        raise ValueError("Secret must be a JSON object")
    values = {}
    for key in SECRET_KEYS & secret.keys():
        value = secret[key]
        if not isinstance(value, str) or not value or "\0" in value:
            raise ValueError(f"Secret key must be a non-empty string: {key}")
        values[key] = value
    for key in ("DB_NAME", "DB_USER"):
        if key not in values and config.get(key.lower()):
            values[key] = config[key.lower()]
    missing = REQUIRED_KEYS - values.keys()
    if missing:
        raise ValueError("Missing Secret keys: " + ", ".join(sorted(missing)))
    if len(values["DJANGO_SECRET_KEY"]) < 50:
        raise ValueError("DJANGO_SECRET_KEY must have at least 50 characters")
    values.setdefault("REDIS_URL", config["redis_url"])
    values.setdefault("REFERENCE_CACHE_URL", values["REDIS_URL"])
    if not all(values[key].startswith("rediss://") for key in ("REDIS_URL", "REFERENCE_CACHE_URL")):
        raise ValueError("Production Valkey connections must use rediss://")
    values.update(
        {
            "ERP_DOMAIN": config["public_host"],
            "ERP_REGISTRY": config["registry"],
            "ERP_IMAGE_TAG": ROOT.name,
            "ERP_RDS_CA_FILE": config["rds_ca_file"],
            "DB_HOST": config["db_host"],
            "DJANGO_ALLOWED_HOSTS": config["public_host"],
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://" + config["public_host"],
        }
    )
    # Never forward AWS credentials, loader state or unrelated host environment to Compose.
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return {
        **{
            k: v
            for k, v in os.environ.items()
            if k
            in {
                "HOME",
                "PATH",
                "XDG_RUNTIME_DIR",
                "DOCKER_CONFIG",
            }
        },
        **values,
        "XDG_RUNTIME_DIR": runtime_dir,
        "DOCKER_HOST": "unix://" + runtime_dir + "/docker.sock",
    }


def ready(host, attempts=30):
    for _ in range(attempts):
        try:
            request = urllib.request.Request(
                "http://127.0.0.1:8080/api/health/",
                headers={"Host": host},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
            if (
                data.get("status") == "online"
                and data.get("end_to_end", {}).get("status") == "connected"
            ):
                return
        except (OSError, ValueError):
            pass
        time.sleep(2)
    raise RuntimeError("Application readiness failed (database/cache/workforce)")


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in {"start", "stop", "preflight", "secret-keys"}:
        raise ValueError("Expected start, stop, preflight or secret-keys")
    config = json.loads(CONFIG.read_text())
    if action != "stop" and "ERP_SECRET_JSON" not in os.environ:
        # Only references reach asm-exec; resolved values stay in process environment.
        child_env = {
            **os.environ,
            "AWS_REGION": config["region"],
            "AWS_TOKEN": "file:///run/erp-secrets/token",
            "ASM_EXEC_LOCAL_ONLY": "true",
            "ERP_SECRET_JSON": "{{resolve:secretsmanager:"
            + config["secret_arn"]
            + ":SecretString}}",
        }
        if config.get("django_secret_arn"):
            child_env["ERP_DJANGO_SECRET_KEY"] = (
                "{{resolve:secretsmanager:"
                + config["django_secret_arn"]
                + ":SecretString:DJANGO_SECRET_KEY}}"
            )
        os.execve(
            sys.executable,
            [
                sys.executable,
                "/usr/local/lib/erp/asm_exec.py",
                "--",
                sys.executable,
                str(Path(__file__).resolve()),
                action,
            ],
            child_env,
        )
    if action == "stop":
        secret = {key: "unused-stop-placeholder-" * 3 for key in REQUIRED_KEYS}
    else:
        secret = json.loads(os.environ.pop("ERP_SECRET_JSON"))
        if "ERP_DJANGO_SECRET_KEY" in os.environ and isinstance(secret, dict):
            secret["DJANGO_SECRET_KEY"] = os.environ.pop("ERP_DJANGO_SECRET_KEY")
    if action == "secret-keys":
        # Values must never appear in output, including diagnostics.
        if not isinstance(secret, dict):
            raise ValueError("Secret must be a JSON object")
        print("Recognized Secret keys: " + ", ".join(sorted(SECRET_KEYS & secret.keys())))
        environment(config, secret)
        print("Required Secret keys and TLS URLs validated")
        return
    env = environment(config, secret)
    if action == "stop":
        operate(action, config, env)
        return
    # Renew registry credentials on every start, including after reboot.
    with tempfile.TemporaryDirectory(prefix="erp-docker-") as auth:
        env["DOCKER_CONFIG"] = auth
        password = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", config["region"]],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", config["registry"]],
            input=password.stdout,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        operate(action, config, env)


def operate(action, config, env):
    compose = [
        "docker",
        "compose",
        "--project-name",
        "erp",
        "-f",
        str(ROOT / "deploy/aws/compose.yml"),
    ]

    def run(*args):
        subprocess.run([*compose, *args], env=env, check=True)

    if action == "stop":
        run("stop", "--timeout", "45")
        return
    run("pull", "--quiet")
    run(
        "run",
        "--rm",
        "--no-deps",
        "backend",
        "python",
        "manage.py",
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
    )
    # Read-only schema/connection check: never initialize or migrate the shared RDS.
    code = (
        "from django.db import connection; "
        "from django.apps import apps; "
        "tables=set(connection.introspection.table_names()); "
        "required={m._meta.db_table for m in apps.get_models() if m._meta.managed}; "
        "missing=required-tables; "
        "print('Schema ready' if not missing else 'Schema baseline required'); "
        "raise SystemExit(bool(missing))"
    )
    run("run", "--rm", "--no-deps", "backend", "python", "manage.py", "shell", "-c", code)
    if action == "preflight":
        return
    run("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
    ready(config["public_host"])
    print("Application ready: " + ROOT.name)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        # Parsing errors may contain input; report only explicit validation errors.
        if isinstance(error, json.JSONDecodeError):
            print("Invalid JSON configuration or Secret", file=sys.stderr)
        elif isinstance(error, subprocess.CalledProcessError):
            print("Deployment command failed; inspect restricted service logs", file=sys.stderr)
        else:
            print(str(error), file=sys.stderr)
        sys.exit(1)
