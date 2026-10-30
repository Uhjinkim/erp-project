import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

AWS = Path(__file__).resolve().parents[1] / "aws"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, AWS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load("runtime", "runtime.py")
release = load("release", "erp-release.py")
metadata = load("metadata", "initialize_metadata.py")

CONFIG = {
    "public_host": "192.0.2.1",
    "registry": "registry.example.com",
    "rds_ca_file": "/unused/ca.pem",
    "db_host": "db.example.com",
    "redis_url": "rediss://cache.example.com:6379/0",
}
SECRET = {
    "DJANGO_SECRET_KEY": "test-only-key-" * 6,
    "DB_NAME": "unused",
    "DB_USER": "unused",
    "DB_PASSWORD": "test-only-password",
}


class EnvironmentTests(unittest.TestCase):
    def test_postgresql_varchar_array_cast_forms_compare_equally(self):
        source = (
            "CHECK (state::text = ANY ((ARRAY['draft'::character varying, "
            "'done'::character varying])::text[]))"
        )
        restored = (
            "CHECK (state::text = ANY (ARRAY[('draft'::character varying)::text, "
            "('done'::character varying)::text]))"
        )
        self.assertEqual(metadata.normalize_constraint(source), restored)
        unrelated = "CHECK (amount::numeric >= 0 AND flags = ARRAY[1, 2])"
        self.assertEqual(metadata.normalize_constraint(unrelated), unrelated)

    def test_allowlist_and_literal_secret_are_preserved(self):
        secret = {
            **SECRET,
            "DB_PASSWORD": "literal$'\"${EVIL}\\\nvalue",
            "DJANGO_SETTINGS_MODULE": "attacker",
            "DB_HOST": "attacker",
        }
        with patch.dict(
            os.environ, {"AWS_SECRET_ACCESS_KEY": "unused", "ERP_SECRET_JSON": "must-not-propagate"}
        ):
            env = runtime.environment(CONFIG, secret)
        self.assertEqual(env["DB_PASSWORD"], secret["DB_PASSWORD"])
        self.assertEqual(env["DB_HOST"], CONFIG["db_host"])
        self.assertNotIn("DJANGO_SETTINGS_MODULE", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertNotIn("ERP_SECRET_JSON", env)

    def test_temporary_registry_config_keeps_explicit_rootless_socket(self):
        with patch.dict(
            os.environ,
            {
                "XDG_RUNTIME_DIR": "/run/user/1002",
                "DOCKER_CONFIG": "/tmp/test-only-auth",
                "DOCKER_CONTEXT": "default",
                "DOCKER_HOST": "unix:///var/run/docker.sock",
            },
        ):
            env = runtime.environment(CONFIG, SECRET)
        self.assertEqual(env["DOCKER_HOST"], "unix:///run/user/1002/docker.sock")
        self.assertEqual(env["DOCKER_CONFIG"], "/tmp/test-only-auth")
        self.assertNotIn("DOCKER_CONTEXT", env)

    def test_configured_valkey_endpoint_overrides_old_secret_placeholder(self):
        env = runtime.environment(CONFIG, {**SECRET, "REDIS_URL": "rediss://placeholder:6379"})
        self.assertEqual(env["REDIS_URL"], CONFIG["redis_url"])
        authenticated = "rediss://test-user:test-only-password@cache.example.com:6379/0"
        env = runtime.environment(
            {**CONFIG, "redis_url": None}, {**SECRET, "REDIS_URL": authenticated}
        )
        self.assertEqual(env["REDIS_URL"], authenticated)

    def test_invalid_secrets_fail_without_echoing_value(self):
        for secret in [
            {},
            {**SECRET, "DB_PASSWORD": 123},
            {**SECRET, "REFERENCE_CACHE_URL": "redis://sensitive-value"},
            {**SECRET, "DJANGO_SECRET_KEY": "sensitive-value"},
        ]:
            with self.subTest(secret_type=type(secret).__name__):
                with self.assertRaises(ValueError) as caught:
                    runtime.environment(CONFIG, secret)
                self.assertNotIn("sensitive-value", str(caught.exception))

    def test_stop_does_not_resolve_secrets_or_authenticate(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_file = Path(temporary) / "runtime.json"
            config_file.write_text(json.dumps(CONFIG))
            with (
                patch.object(runtime, "CONFIG", config_file),
                patch.object(sys, "argv", ["runtime.py", "stop"]),
                patch.object(runtime.os, "execve") as resolve,
                patch.object(runtime.subprocess, "run") as run,
            ):
                runtime.main()
            resolve.assert_not_called()
            self.assertEqual(len(run.call_args_list), 1)
            self.assertEqual(run.call_args.args[0][-3:], ["stop", "--timeout", "45"])

    def test_secret_reference_is_single_pass(self):
        wrapper = load("asm_exec", "asm_exec.py")
        with patch.object(
            wrapper, "resolve_one", return_value="{{resolve:secretsmanager:literal}}"
        ) as resolve:
            actual = wrapper.resolve_string("{{resolve:secretsmanager:test-only}}")
        self.assertEqual(actual, "{{resolve:secretsmanager:literal}}")
        resolve.assert_called_once_with("test-only")


class ReleaseTests(unittest.TestCase):
    def test_archive_rejects_traversal_and_symlinks(self):
        for name, member_type in [
            ("../escape", tarfile.REGTYPE),
            ("deploy/link", tarfile.SYMTYPE),
            ("etc/escape", tarfile.REGTYPE),
        ]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                archive = Path(temporary) / "archive.tar"
                with tarfile.open(archive, "w") as bundle:
                    entry = tarfile.TarInfo(name)
                    entry.type = member_type
                    entry.linkname = "/etc/passwd" if member_type == tarfile.SYMTYPE else ""
                    bundle.addfile(entry)
                with self.assertRaises(ValueError):
                    release.extract(archive, Path(temporary) / "out")

    def test_start_failure_restores_previous_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            old, new = base / "old", base / "new"
            old.mkdir()
            new.mkdir()
            (base / "current").symlink_to(old)
            starts = []

            def run(command, **kwargs):
                if command == ["systemctl", "--user", "start", "erp"]:
                    starts.append((base / "current").resolve())
                    if len(starts) == 1:
                        raise subprocess.CalledProcessError(1, command)

            with (
                patch.object(release, "BASE", base),
                patch.object(release.subprocess, "run", side_effect=run),
                patch("sys.stderr", io.StringIO()),
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    release.activate(new)
            self.assertEqual(starts, [new, old])
            self.assertEqual((base / "current").resolve(), old)

    def test_preflight_failure_keeps_running_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            old, new = base / "old", base / "new"
            old.mkdir()
            new.mkdir()
            (base / "current").symlink_to(old)
            with (
                patch.object(release, "BASE", base),
                patch.object(
                    release.subprocess,
                    "run",
                    side_effect=subprocess.CalledProcessError(1, ["preflight"]),
                ) as run,
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    release.activate(new)
            self.assertEqual(len(run.call_args_list), 1)
            self.assertEqual((base / "current").resolve(), old)


if __name__ == "__main__":
    unittest.main()
