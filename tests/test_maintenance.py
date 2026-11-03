import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import health  # noqa: E402
import triage  # noqa: E402


# health ---------------------------------------------------------------------

def test_cran_status_reports_the_worst_result():
    assert health.cran_status("<td>OK</td><td>NOTE</td>") == "NOTE"
    assert health.cran_status("<td>OK</td><td>WARN</td><td>NOTE</td>") == "WARN"
    assert health.cran_status("<td>ERROR</td><td>OK</td>") == "ERROR"
    assert health.cran_status("nothing here") == "unknown"


def test_latest_ci_takes_the_newest_completed_ci_run():
    runs = {"workflow_runs": [
        {"name": "Pages", "status": "completed", "conclusion": "failure", "html_url": "p"},
        {"name": "CI", "status": "in_progress", "conclusion": None, "html_url": "a"},
        {"name": "CI", "status": "completed", "conclusion": "success", "html_url": "b"},
    ]}
    assert health.latest_ci(json.dumps(runs)) == ("success", "b")
    assert health.latest_ci("") == ("none", None)


def test_collect_and_render_flag_problems_without_network():
    config = {"owner": "o", "catalogue": "cat", "repositories": [
        {"repo": "good", "cran": "goodpkg", "site": "https://site/good/"},
        {"repo": "bad", "cran": "badpkg", "site": "https://site/bad/"},
    ]}
    catalogue = {"components": [{"id": "x", "repository": "https://github.com/o/x", "url": None}]}

    def fake_get(url, token=None, method="GET"):
        if "actions/runs" in url:
            ok = "success" if "/good/" in url else "failure"
            return 200, json.dumps({"workflow_runs": [{"name": "CI", "status": "completed", "conclusion": ok, "html_url": "u"}]})
        if "check_results_goodpkg" in url:
            return 200, "<td>OK</td>"
        if "check_results_badpkg" in url:
            return 200, "<td>WARN</td>"
        if url == "cat":
            return 200, json.dumps(catalogue)
        if url == "https://site/bad/":
            return 404, ""
        if url == "https://github.com/o/x":
            return 404, ""
        if url.startswith(health.API + "/repos/"):
            return 200, json.dumps({"open_issues_count": 2})
        return 200, ""

    rows, broken = health.collect(config, get=fake_get)
    assert rows[0]["problems"] == []
    assert rows[1]["problems"] == ["CI failing on the default branch", "CRAN reports WARN", "website answers 404"]
    assert broken == [("x", "https://github.com/o/x", 404)]
    report, n = health.render(rows, broken)
    assert n == 2
    assert "| good |" in report and "website answers 404" in report


# triage ---------------------------------------------------------------------

def test_classify_recognises_common_failures():
    assert triage.classify("Error: there is no package called 'xml2'") == "dependency"
    assert triage.classify("Timeout was reached: [cran.r-project.org]") == "network"
    assert triage.classify("Status: 1 WARNING, 2 NOTEs") == "check-warning"
    assert triage.classify("[ FAIL 3 | WARN 0 | SKIP 0 | PASS 40 ]") == "test-failure"
    assert triage.classify("something odd") == "unknown"


def test_high_risk_paths_come_from_codeowners():
    owners = "# comment\n/R/signals.R @me\n/inst/extdata/ @me\n/.github/ @me\n"
    pats = triage.high_risk_patterns(owners)
    changed = ["R/signals.R", "R/utils.R", "inst/extdata/tortured_phrases.csv", "README.md"]
    assert triage.touches_high_risk(changed, pats) == ["R/signals.R", "inst/extdata/tortured_phrases.csv"]
    assert triage.risk("dependency", ["R/signals.R"]) == "maintainer-review"
    assert triage.risk("dependency", []) == "routine"
    assert triage.risk("test-failure", []) == "review"


def test_without_api_key_the_issue_says_so(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert triage.ask_claude("log", "unknown", []) is None
    body = triage.issue_body("dependency", "routine", [], None, "https://run", False)
    assert "ANTHROPIC_API_KEY" in body and "`dependency`" in body


def test_claude_request_and_issue_with_a_fake_client():
    sent = {}

    class Messages:
        def create(self, **kw):
            sent.update(kw)
            answer = {"likely_cause": "xml2 missing on R devel", "proposed_fix": "Add libxml2-dev to the CI system dependencies.",
                      "affects_scientific_method": False, "confidence": "medium"}
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(answer))])

    client = SimpleNamespace(beta=SimpleNamespace(messages=Messages()))
    d = triage.ask_claude("there is no package called 'xml2'", "dependency", ["DESCRIPTION"], client=client)
    assert sent["model"] == "claude-opus-5-5"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert "Never propose changing a scientific method" in sent["system"]
    assert "<log>" in sent["messages"][0]["content"]
    body = triage.issue_body("dependency", "maintainer-review", ["R/signals.R"], d, "https://run", True)
    assert "High-risk files changed" in body
    assert "Nothing was changed in the repository" in body
    assert "end of the failed steps' log" in body


def test_refusals_and_method_changes_are_reported_not_hidden():
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(stop_reason="refusal", content=[]))))
    d = triage.ask_claude("log", "unknown", [], client=client)
    assert "refusal" in d["error"]
    method = {"likely_cause": "c", "proposed_fix": "f", "affects_scientific_method": True, "confidence": "low"}
    assert "the maintainer decides" in triage.issue_body("test-failure", "review", [], method, None, False)
