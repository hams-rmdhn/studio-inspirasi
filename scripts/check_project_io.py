#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check the actual host project-storage module without native media/UI libraries.

The temporary crate reuses the source, dependency versions and lockfile from this
checkout. It never copies implementation logic or changes the workspace lockfile.
This narrow check complements the full host/release CI.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use already cached dependencies")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    workspace = root / "src"
    lock = (workspace / "Cargo.lock").read_bytes()
    packages = tomllib.loads(lock.decode())["package"]
    version = tomllib.loads((workspace / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    with tempfile.TemporaryDirectory(prefix="clovercut-project-io-") as directory:
        scratch = Path(directory)
        manifest = (
            '[package]\nname = "clovercut-project-io-check"\n'
            f'version = {json.dumps(version)}\nedition = "2024"\n'
            f'[lib]\npath = {json.dumps(str(workspace / "crates/concat-host/src/projects.rs"))}\n'
            '[dependencies]\n'
        )
        for name in ("serde", "serde_json", "log", "tempfile"):
            versions = {package["version"] for package in packages if package["name"] == name}
            if len(versions) != 1:
                parser.error(f"ambiguous locked versions for {name}; update the isolated check")
            pinned = json.dumps("=" + versions.pop())
            manifest += (f'{name} = {{ version = {pinned}, features = ["derive"] }}\n'
                         if name == "serde" else f'{name} = {pinned}\n')
        manifest += 'concat-project = { path = ' + json.dumps(str(workspace / "crates/concat-project")) + ' }\n'
        (scratch / "Cargo.toml").write_text(manifest)
        (scratch / "Cargo.lock").write_bytes(lock)
        env = os.environ.copy()
        env.setdefault("CARGO_TARGET_DIR", str(workspace / "target"))
        env.setdefault("CARGO_BUILD_JOBS", "2")
        for command, options in (
                ("clippy", ["--all-targets", "--", "-D", "warnings"]),
                ("test", ["--lib"])):
            process = subprocess.run(
                ["cargo", command, "--manifest-path", str(scratch / "Cargo.toml"),
                 *(["--offline"] if args.offline else []), *options],
                cwd=workspace, env=env, check=False,
            )
            if process.returncode:
                return process.returncode
    if (workspace / "Cargo.lock").read_bytes() != lock:
        raise RuntimeError("workspace lockfile changed during isolated project checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
