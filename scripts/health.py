"""Weekly health report for every repository listed in ecosystem.json.

For each repository: the latest CI run on the default branch, open issues and
pull requests, the CRAN check status of its package, and whether its website
and the links of the metascience catalogue answer. Read-only: it never
changes anything. Uses the GitHub REST API with GITHUB_TOKEN when present.

Usage: python scripts/health.py ecosystem.json > report.md
Exit status is 0 even when problems are found; the report says what to fix.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def http_get(url, token=None, method="GET", timeout=30):
    """Return (status, body). Network errors give status 0."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "research-tools-ops"})
    if token and url.startswith(API):
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace") if method == "GET" else ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


def cran_status(html):
    """Worst CRAN check result on a check_results page: ERROR > WARN > NOTE > OK."""
    found = set(re.findall(r">(ERROR|WARN|FAIL|NOTE|OK)<", html))
    for level in ("ERROR", "FAIL", "WARN", "NOTE", "OK"):
        if level in found:
            return level
    return "unknown"


def latest_ci(runs_json):
    """Conclusion of the most recent completed run of a workflow named CI."""
    runs = json.loads(runs_json).get("workflow_runs", []) if runs_json else []
    for r in runs:
        if r.get("name") == "CI" and r.get("status") == "completed":
            return r.get("conclusion") or "unknown", r.get("html_url")
    return "none", None


def catalogue_links(catalogue_json):
    """Every repository and url of the metascience catalogue."""
    cat = json.loads(catalogue_json)
    links = []
    for c in cat.get("components", []):
        for key in ("repository", "url"):
            if c.get(key):
                links.append((c["id"], c[key]))
    return links


def problems(row):
    """Human-readable problems for one repository row; empty when healthy."""
    out = []
    if row["ci"] == "failure":
        out.append("CI failing on the default branch")
    if row["cran"] in ("ERROR", "FAIL", "WARN"):
        out.append("CRAN reports " + row["cran"])
    if row["site"] not in (None, 200):
        out.append("website answers %s" % row["site"])
    return out


def collect(config, token=None, get=http_get):
    owner = config["owner"]
    rows = []
    for entry in config["repositories"]:
        repo = entry["repo"]
        _, runs = get("%s/repos/%s/%s/actions/runs?per_page=20&exclude_pull_requests=true" % (API, owner, repo), token)
        ci, ci_url = latest_ci(runs)
        _, info = get("%s/repos/%s/%s" % (API, owner, repo), token)
        open_items = json.loads(info).get("open_issues_count", "?") if info else "?"
        cran = "-"
        if entry.get("cran"):
            status, html = get("https://cran.r-project.org/web/checks/check_results_%s.html" % entry["cran"])
            cran = cran_status(html) if status == 200 else ("not on CRAN" if status == 404 else "unreachable")
        site = None
        if entry.get("site"):
            site, _ = get(entry["site"], method="HEAD")
        row = {"repo": repo, "ci": ci, "ci_url": ci_url, "open": open_items, "cran": cran, "site": site}
        row["problems"] = problems(row)
        rows.append(row)
    broken = []
    if config.get("catalogue"):
        status, body = get(config["catalogue"])
        if status == 200:
            for cid, url in catalogue_links(body):
                code, _ = get(url, method="HEAD")
                if code == 405:  # Some hosts refuse HEAD.
                    code, _ = get(url)
                if not 200 <= code < 400:
                    broken.append((cid, url, code))
    return rows, broken


def render(rows, broken):
    lines = ["# Ecosystem health", "",
             "| Repository | CI | Open issues + PRs | CRAN | Website | Problems |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        ci = "[%s](%s)" % (r["ci"], r["ci_url"]) if r["ci_url"] else r["ci"]
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            r["repo"], ci, r["open"], r["cran"], r["site"] if r["site"] is not None else "-",
            "; ".join(r["problems"]) or "none"))
    lines += ["", "## Catalogue links", ""]
    if broken:
        lines += ["- %s: %s answers %s" % b for b in broken]
    else:
        lines.append("All repository and website links of the metascience catalogue answer.")
    n = sum(1 for r in rows if r["problems"]) + len(broken)
    lines += ["", "**%d problem(s) need attention.**" % n if n else "**Nothing needs attention.**"]
    return "\n".join(lines) + "\n", n


def main(argv):
    config = json.load(open(argv[1], encoding="utf-8"))
    rows, broken = collect(config, os.environ.get("GITHUB_TOKEN"))
    report, n = render(rows, broken)
    sys.stdout.write(report)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("problems=%d\n" % n)


if __name__ == "__main__":
    main(sys.argv)
