# research-tools-ops

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23881629.svg)](https://doi.org/10.5281/zenodo.23881629)

Shared GitHub Actions workflows that keep open research software published and healthy with as little routine work as possible. Routine work is automated; anything that changes a scientific method or how evidence is read always waits for the maintainer.

| Workflow | Used by | Does |
| --- | --- | --- |
| `cran-watch.yml` | uxlearn, narrativecv, reproimage, visualbrief, abfunnel, neuroconsumer, aitrail, scicomm, academiccareer, photoarchive (every Wednesday) | Reads the package's public CRAN check results and fails if any platform reports ERROR, WARN or FAIL, so problems surface before CRAN's deadline. When CRAN publishes a new version, it creates the matching GitHub release, and Zenodo mints its DOI. |
| `auto-release.yml` | openresearchmetrics, ixd-lab (first day of each month) | If `main` changed and the tests pass, tags a patch release and publishes it; Zenodo mints its DOI. The version bump lives only on the tag, so `main` stays protected. |
| `ecosystem-health.yml` | this repository (every Monday) | One report for every repository in [`ecosystem.json`](ecosystem.json): CI on the default branch, open issues and pull requests, CRAN checks, websites, and every link of the metascience catalogue. Keeps one open **Ecosystem health** issue up to date and comments when something needs attention. Read-only. |
| `failure-triage.yml` | metascience, FoSci, reproducibility, AIRes (when CI fails on main) | Classifies the failure (dependency, network, check warning or error, test failure, documentation), marks its risk from the repository's CODEOWNERS, and, if the `ANTHROPIC_API_KEY` secret is set, adds a diagnosis and proposed fix from Claude. Opens or updates one **CI failure on main** issue. It never edits code or opens pull requests. |

Every project also runs its own CI on every change and weekly against the newest versions of its dependencies. GitHub emails the maintainer when a scheduled run fails or an issue is opened.

## What is automated and what is not

| Change | Automated | Needs the maintainer |
| --- | --- | --- |
| Checks, monitoring, health reports, alerts | yes | – |
| Failure diagnosis and fix proposals | proposed in an issue | applying any fix |
| Patch releases of non-CRAN tools when tests pass | yes | – |
| Indicator definitions, catalogues, crosswalks, thresholds, expected test results | never | always (CODEOWNERS) |
| Breaking API changes, CRAN submissions, security-sensitive changes | never | always |

A failure that touches a CODEOWNERS path is labelled `risk:maintainer-review`. The AI diagnosis is told never to propose changing a scientific method or an expected result to make a test pass, and to say "unknown" when the log does not show the cause. The rules come from the [metascience governance](https://github.com/pablosancheznunez/metascience/blob/main/docs/GOVERNANCE.md).

## Using it

```yaml
jobs:
  cran:
    uses: pablosancheznunez/research-tools-ops/.github/workflows/cran-watch.yml@main
    permissions:
      contents: write
    with:
      package: yourpackage

  triage:
    needs: [r-package]
    if: failure() && github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    uses: pablosancheznunez/research-tools-ops/.github/workflows/failure-triage.yml@main
    permissions:
      contents: read
      actions: read
      issues: write
    secrets: inherit
```

`auto-release.yml` reads the files to bump from `.maintenance.json`:

```json
{ "release": { "version_files": ["CITATION.cff", "DESCRIPTION"] } }
```

**AI diagnosis (optional).** Add an Anthropic API key as the repository or account secret `ANTHROPIC_API_KEY`. Without it the triage still classifies failures and marks their risk with fixed rules, and no log leaves GitHub. With it, the end of the failed steps' log is sent to the Claude API (model `claude-opus-5-5`).

## Tests

```bash
python -m pytest -q
```

## Citation and license

See [`CITATION.cff`](CITATION.cff). MIT License.
