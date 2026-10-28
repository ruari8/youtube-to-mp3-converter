#!/usr/bin/env python3
"""Register the local Chrome bridge. Safe to rerun after moving the repo."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
HOST = "local.yt2mp3"


def extension_id():
    manifest = json.loads((ROOT / "extension" / "manifest.json").read_text())
    digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
    return "".join(chr(ord("a") + int(char, 16)) for char in digest)


def install(destination, runtime):
    pipx_python = Path.home() / ".local/pipx/venvs/yt2mp3/bin/python"
    python = pipx_python if pipx_python.exists() else ROOT / "venv" / "bin" / "python"
    if not python.exists():
        raise SystemExit("Create the repo's venv and install requirements.txt first.")
    # Chrome cannot reliably launch native hosts from macOS-protected Documents folders.
    # Install a snapshot in Application Support; rerunning this script updates it.
    runtime.mkdir(parents=True, exist_ok=True)
    for name in ("native_host.py", "yt2mp3.py"):
        shutil.copyfile(ROOT / name, runtime / name)
    launcher = runtime / "chrome-native-host"
    # Finder-launched Chrome does not inherit the user's shell PATH.
    launcher.write_text("#!/bin/sh\nexport PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\n"
                        + "exec " + shlex.quote(str(python)) + " " + shlex.quote(str(runtime / "native_host.py")) + ' "$@"\n')
    launcher.chmod(0o755)
    manifest = {"name": HOST, "description": "yt2mp3 local downloader", "path": str(launcher),
                "type": "stdio", "allowed_origins": [f"chrome-extension://{extension_id()}/"]}
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{HOST}.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Registered helper: {target}")
    print(f"Load unpacked extension: {ROOT / 'extension'}")
    print(f"Extension ID: {extension_id()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts")
    parser.add_argument("--runtime", type=Path, default=Path.home() / "Library/Application Support/yt2mp3")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This installer currently supports macOS.")
    install(args.destination, args.runtime)
