# research-tools-ops

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23881629.svg)](https://doi.org/10.5281/zenodo.23881629)

Shared maintenance for open research software: keep tools working with minimal human time, while every change to scientific content waits for a maintainer.

It serves these projects:

| Project | What it is |
| --- | --- |
| [narrative-cv-crosswalk](https://github.com/pablosancheznunez/narrative-cv-crosswalk) | Narrative CV sections linked to evidence in ORCID, OpenAlex, DataCite and OpenAIRE |
| [openresearchmetrics](https://github.com/pablosancheznunez/openresearchmetrics) | Transparent open science indicators, each with its evidence and limits |
| [reproimage](https://github.com/pablosancheznunez/reproimage) | Integrity, provenance and reproducibility checks for scientific images |
| [uxlearn](https://github.com/pablosancheznunez/uxlearn) | R package for learning user experience |
| [synthviscom](https://github.com/pablosancheznunez/synthviscom) | Synthetic dataset for visual communication research |
| [ixd-lab](https://github.com/pablosancheznunez/ixd-lab) | Learning environment for interaction design |

## What runs, and when

| Reusable workflow | Called by each project on | Does |
| --- | --- | --- |
| `risk-gate.yml` | every pull request | Labels the change `risk:low`, `risk:medium` or `risk:high` from the paths it touches, and auto-merges Dependabot and `repair/*` changes below high once CI passes |
| `repair.yml` | a failed CI or weekly live check on `main` | Asks the configured repair agent for a fix, opens a pull request and sends it through the same gate; without an agent, opens an issue |
| `auto-release.yml` | the first day of each month | If `main` changed and the tests pass, tags a patch release and publishes it; Zenodo mints the version DOI |

## Rules enforced in code

1. **Risk is decided by paths, not by a model.** [`scripts/risk.py`](scripts/risk.py) reads each project's `.maintenance.json`. Workflows, `.maintenance.json`, `CONTRIBUTING.md` and expected results are always high risk.
2. **High risk never merges by itself.** It gets `needs-human`; `CODEOWNERS` and a branch ruleset require the maintainer's approval.
3. **Bounded attempts.** At most one open automatic repair at a time and three in seven days, then a `needs-attention` issue.
4. **Least privilege.** The repair agent only edits files; the workflow commits them with a token that cannot change workflows. Publication to Zenodo goes through GitHub's own integration, so no publishing credential is ever exposed.
5. **Releases never touch `main`.** The version bump lives only on the release tag, so `main` stays protected with no exceptions.
6. **Works without an agent.** If none is configured, failures become issues and everything else (Dependabot, auto-merge, releases) keeps running.

## Adding a project

1. Add `.github/workflows/maintenance.yml` calling the three workflows (see any project above) and a `.maintenance.json`:

   ```json
   {
     "risk_paths": {
       "high": ["data/**", "schema/**", "tests/regression/**"],
       "low": ["docs/**", "README.md"]
     },
     "release": { "version_files": ["CITATION.cff"] }
   }
   ```

2. Add a `CONTRIBUTING.md` with the test command and the files that must not change without review, and a `CODEOWNERS` for the high-risk paths.
3. Switch the repository on in Zenodo to get a DOI per release.
4. Optional: configure a repair agent with the repository variables `REPAIR_AGENT_SETUP` and `REPAIR_AGENT_RUN` and the secret `REPAIR_AGENT_KEY` (any coding-agent command line tool that can edit files from a task description; the task is written to `/tmp/repair-task.md`).

## Tests

```bash
python -m pytest -q
```

## Citation and license

See [`CITATION.cff`](CITATION.cff). MIT License.
