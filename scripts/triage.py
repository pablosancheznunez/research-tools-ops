"""Triage of a failed CI run: what kind of failure it is, how risky a fix
would be, and (when ANTHROPIC_API_KEY is set) a proposed diagnosis from
Claude. It writes an issue body; it never edits code, opens pull requests or
changes settings.

Usage:
  python scripts/triage.py LOG_FILE CHANGED_FILES_FILE CODEOWNERS_FILE > issue.md

Governance (metascience docs/GOVERNANCE.md): a failure that touches a
high-risk path (methods, catalogues, thresholds, expected outputs, all listed
in CODEOWNERS) is always marked for the maintainer, and the proposal may
never be to change a scientific method or an expected result to make a test
pass.
"""
import fnmatch
import json
import os
import re
import sys

MODEL = "claude-opus-5-5"

# First matching rule wins; ordered from most to least specific.
RULES = [
    ("dependency", r"(there is no package called|dependency .* is not available|ERROR: dependenc|"
                   r"Could not resolve|unable to install|npm ERR!|No matching distribution)"),
    ("network", r"(Timeout was reached|Could not resolve host|HTTP error 5\d\d|Connection (reset|refused)|"
                r"cannot open URL|ECONNRESET|rate limit)"),
    ("check-warning", r"(Status: \d+ WARNINGs?|checking .* \.\.\. WARNING)"),
    ("check-error", r"(Status: \d+ ERRORs?|checking .* \.\.\. ERROR)"),
    ("test-failure", r"(\[ FAIL [1-9]|Failure \(|FAILED tests?/|AssertionError|not ok \d+)"),
    ("documentation", r"(Undocumented code objects|Rd files with|codoc mismatches|pkgdown)"),
]


def classify(log):
    for name, pattern in RULES:
        if re.search(pattern, log, re.IGNORECASE):
            return name
    return "unknown"


def high_risk_patterns(codeowners_text):
    """Paths in CODEOWNERS, which in these repositories mark high-risk files."""
    pats = []
    for line in codeowners_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(line.split()[0])
    return pats


def touches_high_risk(changed, patterns):
    hits = []
    for f in changed:
        path = "/" + f.lstrip("/")
        for p in patterns:
            if p.endswith("/") and path.startswith(p):
                hits.append(f)
            elif fnmatch.fnmatch(path, p) or path == p:
                hits.append(f)
    return sorted(set(hits))


def risk(category, high_risk_files):
    if high_risk_files:
        return "maintainer-review"
    if category in ("test-failure", "check-error", "unknown"):
        return "review"
    return "routine"


def log_excerpt(log, max_chars=60000):
    """The end of the failed steps' log, where errors are reported. The
    excerpt is labelled as such in the issue."""
    return log if len(log) <= max_chars else log[-max_chars:]


SYSTEM = """You triage failed CI runs of open research software (R packages and small web tools).
Rules you must follow:
- Diagnose from the log only; say "unknown" when the log does not show the cause.
- Propose the smallest fix. Never propose changing a scientific method, an indicator definition,
  a threshold, a catalogue or an expected test result to make a test pass; if that seems to be the
  issue, say that the maintainer must decide.
- Do not invent package versions, files or functions that the log does not mention."""

SCHEMA = {
    "type": "object",
    "properties": {
        "likely_cause": {"type": "string"},
        "proposed_fix": {"type": "string"},
        "affects_scientific_method": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["likely_cause", "proposed_fix", "affects_scientific_method", "confidence"],
    "additionalProperties": False,
}


def ask_claude(excerpt, category, changed, client=None):
    """Structured diagnosis from Claude, or None without an API key."""
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None
        import anthropic
        client = anthropic.Anthropic()
    prompt = ("Rule-based category: %s\nFiles changed in the triggering commit:\n%s\n\n"
              "Log of the failed steps (end):\n<log>\n%s\n</log>" % (category, "\n".join(changed) or "(none)", excerpt))
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        return {"error": "No diagnosis (stop reason: %s)." % response.stop_reason}
    text = "".join(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def issue_body(category, level, high_risk_files, diagnosis, run_url, truncated):
    lines = ["Automatic triage of a failed CI run: %s" % (run_url or "(run URL unavailable)"), "",
             "| | |", "| --- | --- |",
             "| Category | `%s` |" % category,
             "| Risk | `%s` |" % level]
    if high_risk_files:
        lines += ["", "**High-risk files changed** (CODEOWNERS): " + ", ".join("`%s`" % f for f in high_risk_files),
                  "Any fix needs the maintainer's review; methods and expected results are never changed automatically."]
    if diagnosis is None:
        lines += ["", "No AI diagnosis: the `ANTHROPIC_API_KEY` secret is not set. The category comes from fixed rules."]
    elif "error" in diagnosis:
        lines += ["", diagnosis["error"]]
    else:
        lines += ["", "### Proposed diagnosis (Claude, confidence: %s)" % diagnosis["confidence"], "",
                  "**Likely cause.** " + diagnosis["likely_cause"], "",
                  "**Proposed fix.** " + diagnosis["proposed_fix"]]
        if diagnosis["affects_scientific_method"]:
            lines += ["", "**The proposal concerns a scientific method or expected result: the maintainer decides.**"]
        lines += ["", "_This is a proposal, not a verified finding. Nothing was changed in the repository._"]
    if truncated:
        lines += ["", "_The diagnosis used the end of the failed steps' log._"]
    return "\n".join(lines) + "\n"


def main(argv):
    log = open(argv[1], encoding="utf-8", errors="replace").read()
    changed = [l.strip() for l in open(argv[2], encoding="utf-8").read().splitlines() if l.strip()]
    owners = open(argv[3], encoding="utf-8").read() if os.path.exists(argv[3]) else ""
    category = classify(log)
    high = touches_high_risk(changed, high_risk_patterns(owners))
    level = risk(category, high)
    excerpt = log_excerpt(log)
    try:
        diagnosis = ask_claude(excerpt, category, changed)
    except Exception as e:  # The triage must never fail the calling workflow.
        diagnosis = {"error": "AI diagnosis unavailable: %s" % type(e).__name__}
    sys.stdout.write(issue_body(category, level, high, diagnosis, os.environ.get("RUN_URL"), len(excerpt) < len(log)))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("category=%s\nrisk=%s\n" % (category, level))


if __name__ == "__main__":
    main(sys.argv)
