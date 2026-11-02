"""Bump the patch version in every file listed in .maintenance.json.

The current version is read from CITATION.cff. Prints the new version.
Usage: python bump.py <maintenance.json>
"""

import json
import re
import sys
from pathlib import Path


def current_version(root):
    text = (root / "CITATION.cff").read_text(encoding="utf-8")
    return re.search(r'^version:\s*"?(\d+\.\d+\.\d+)"?', text, re.M).group(1)


def next_patch(version):
    major, minor, patch = (int(x) for x in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def bump(root, files, old, new):
    for name in files:
        path = root / name
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(f"{name} does not contain version {old}")
        path.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    policy_path = Path(sys.argv[1])
    root = policy_path.parent
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    old = current_version(root)
    new = next_patch(old)
    bump(root, policy["release"]["version_files"], old, new)
    print(new)
