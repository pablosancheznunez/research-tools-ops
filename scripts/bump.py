"""Bump the patch version in every file listed in .maintenance.json.

Release commits live only on their tag, never on main, so main keeps the
version of its last manual edit. The next version is one patch above the
higher of that version and the latest tag. Prints the new version.

Usage: python bump.py <maintenance.json> [<latest tag version>]
"""

import json
import re
import sys
from pathlib import Path


def current_version(root):
    text = (root / "CITATION.cff").read_text(encoding="utf-8")
    return re.search(r'^version:\s*"?(\d+\.\d+\.\d+)"?', text, re.M).group(1)


def parse(version):
    return tuple(int(x) for x in version.split("."))


def next_patch(version):
    major, minor, patch = parse(version)
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
    in_files = current_version(root)
    candidates = [in_files] + [v for v in sys.argv[2:3] if re.fullmatch(r"\d+\.\d+\.\d+", v)]
    new = next_patch(max(candidates, key=parse))
    bump(root, policy["release"]["version_files"], in_files, new)
    print(new)
