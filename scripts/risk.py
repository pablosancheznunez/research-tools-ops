"""Classify a change by risk level from the paths it touches.

The level is decided here, deterministically, never by a language model.
Usage: python risk.py <maintenance.json> <changed-file> [<changed-file> ...]
Prints one word: low, medium or high.
"""

import fnmatch
import json
import sys

ORDER = ["low", "medium", "high"]

# Paths that are high risk in every repository: changing them could weaken
# the controls that keep automatic changes safe.
ALWAYS_HIGH = [".github/*", ".github/**", ".maintenance.json", "CODEOWNERS", "CLAUDE.md"]


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def classify(policy, paths):
    risk_paths = policy.get("risk_paths", {})
    level = "low"
    for path in paths:
        if matches(path, ALWAYS_HIGH) or matches(path, risk_paths.get("high", [])):
            this = "high"
        elif matches(path, risk_paths.get("low", [])):
            this = "low"
        else:
            # Anything not declared low is at least medium.
            this = "medium"
        if ORDER.index(this) > ORDER.index(level):
            level = this
    return level


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        policy = json.load(f)
    print(classify(policy, sys.argv[2:]))
