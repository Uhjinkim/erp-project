#!/usr/bin/env python3
"""Install a checksum-verified release, restart, and restore the previous release on failure."""

import fcntl
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BASE = Path("/srv/erp")


def extract(archive, destination):
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        for member in members:
            path = Path(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != "deploy"
                or not (member.isfile() or member.isdir())
            ):
                raise ValueError("Unsafe release archive")
        bundle.extractall(destination, members=members, filter="data")


def switch(release):
    pending = BASE / "current.new"
    pending.unlink(missing_ok=True)
    pending.symlink_to(release, target_is_directory=True)
    pending.replace(BASE / "current")


def activate(release):
    previous = (BASE / "current").resolve() if (BASE / "current").is_symlink() else None
    # Verify configuration/schema before stopping a working release.
    subprocess.run(
        [sys.executable, str(release / "deploy/aws/runtime.py"), "preflight"], check=True
    )
    subprocess.run(["systemctl", "--user", "stop", "erp"], check=True)
    switch(release)
    try:
        subprocess.run(["systemctl", "--user", "reset-failed", "erp"], check=True)
        subprocess.run(["systemctl", "--user", "start", "erp"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["systemctl", "--user", "stop", "erp"], check=True)
        if previous:
            switch(previous)
            subprocess.run(["systemctl", "--user", "reset-failed", "erp"], check=True)
            subprocess.run(["systemctl", "--user", "start", "erp"], check=True)
            print("Restored previous release", file=sys.stderr)
        raise


def main():
    if (
        len(sys.argv) != 3
        or not re.fullmatch(r"[a-f0-9]{40}", sys.argv[1])
        or not re.fullmatch(r"[a-f0-9]{64}", sys.argv[2])
    ):
        raise ValueError("Expected release commit SHA and archive SHA256")
    sha, checksum = sys.argv[1:]
    config = json.loads(Path("/etc/erp/runtime.json").read_text())
    with (BASE / "deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(prefix="erp-release-") as temporary:
            archive = Path(temporary) / "deploy.tar.gz"
            subprocess.run(
                [
                    "aws",
                    "s3",
                    "cp",
                    "--no-progress",
                    "--only-show-errors",
                    f"s3://{config['release_bucket']}/releases/{sha}/deploy.tar.gz",
                    str(archive),
                    "--region",
                    config["region"],
                ],
                check=True,
            )
            if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
                raise ValueError("Release checksum mismatch")
            release = BASE / "releases" / sha
            if not release.exists():
                staging = Path(temporary) / "content"
                staging.mkdir()
                extract(archive, staging)
                # Temporary directories may be on another filesystem.
                shutil.copytree(staging, release)
            activate(release)
            print("Deployed " + sha)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("Release failed; inspect restricted EC2 service logs", file=sys.stderr)
        sys.exit(1)
