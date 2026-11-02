import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import bump  # noqa: E402
import risk  # noqa: E402

POLICY = {
    "risk_paths": {
        "high": ["data/mappings/*", "tests/regression/*"],
        "low": ["docs/*", "README.md"],
    }
}


def test_docs_only_is_low():
    assert risk.classify(POLICY, ["docs/index.html", "README.md"]) == "low"


def test_undeclared_path_is_medium():
    assert risk.classify(POLICY, ["docs/a.md", "web/app.js"]) == "medium"


def test_highest_level_wins():
    assert risk.classify(POLICY, ["README.md", "data/mappings/r4ri.json"]) == "high"


def test_controls_are_always_high():
    for path in [".github/workflows/ci.yml", ".maintenance.json", "CLAUDE.md"]:
        assert risk.classify({}, [path]) == "high"


def test_regression_expectations_are_high():
    assert risk.classify(POLICY, ["tests/regression/expected.json"]) == "high"


def test_bump(tmp_path):
    (tmp_path / "CITATION.cff").write_text('cff-version: 1.2.0\nversion: "0.1.9"\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('version = "0.1.9"\n', encoding="utf-8")
    old = bump.current_version(tmp_path)
    assert old == "0.1.9"
    new = bump.next_patch(old)
    assert new == "0.1.10"
    bump.bump(tmp_path, ["CITATION.cff", "pyproject.toml"], old, new)
    assert 'version = "0.1.10"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "cff-version: 1.2.0" in (tmp_path / "CITATION.cff").read_text(encoding="utf-8")


def test_bump_starts_from_the_latest_tag(tmp_path):
    # Release commits live only on tags, so main can lag behind them.
    import json
    import subprocess

    (tmp_path / "CITATION.cff").write_text('version: "0.1.0"\n', encoding="utf-8")
    (tmp_path / ".maintenance.json").write_text(json.dumps({"release": {"version_files": ["CITATION.cff"]}}), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "bump.py"
    out = subprocess.run([sys.executable, str(script), str(tmp_path / ".maintenance.json"), "0.1.4"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "0.1.5"
    assert 'version: "0.1.5"' in (tmp_path / "CITATION.cff").read_text(encoding="utf-8")
    out = subprocess.run([sys.executable, str(script), str(tmp_path / ".maintenance.json"), ""], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "0.1.6"
