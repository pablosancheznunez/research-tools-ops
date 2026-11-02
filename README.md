# research-tools-ops

Shared, AI-assisted maintenance for three open research tools:

- [narrative-cv-crosswalk](https://github.com/pablosancheznunez/narrative-cv-crosswalk): links narrative CV sections to evidence in ORCID, OpenAIRE, OpenAlex and DataCite.
- [openresearchmetrics](https://github.com/pablosancheznunez/openresearchmetrics): transparent open science indicators, each with its evidence and limits.
- [reproimage](https://github.com/pablosancheznunez/reproimage): integrity, provenance and reproducibility checks for scientific images.

The products are independent. This repository only holds the machinery that keeps them working with as little human time as possible.

## What runs, and when

| Workflow | Called by each product on | Does |
| --- | --- | --- |
| `risk-gate.yml` | every pull request | Labels the change `risk:low`, `risk:medium` or `risk:high` from the paths it touches; auto-merges Dependabot and `ai/*` changes below high once CI passes |
| `ai-repair.yml` | a failed CI or weekly live check on `main` | Runs Claude Code to propose a fix, opens a pull request and sends it through the same gate; otherwise opens an issue |
| `auto-release.yml` | the first day of each month | If `main` changed and tests pass, bumps the patch version, tags and creates a GitHub release (Zenodo mints the DOI) |

## Rules that are enforced in code

1. **Risk is decided by paths, not by a model.** [`scripts/risk.py`](scripts/risk.py) reads each product's `.maintenance.json`. Workflows, `.maintenance.json`, `CLAUDE.md` and regression expectations are always high.
2. **High risk never merges by itself.** It gets `needs-human`; `CODEOWNERS` and the branch ruleset require the owner's approval.
3. **Bounded attempts.** At most one open repair at a time and three in seven days, then an `ai-blocked` issue.
4. **No secrets for the agent beyond its API key.** The agent edits files only; the workflow commits. Its token cannot change workflows. Publishing to Zenodo happens through GitHub's own integration.
5. **Works without AI.** With no `ANTHROPIC_API_KEY` secret, failures become issues and everything else (Dependabot, auto-merge, releases) keeps running.

## Using it in a product repository

Each product has one `.github/workflows/maintenance.yml` that calls these workflows, plus a `.maintenance.json`:

```json
{
  "risk_paths": {
    "high": ["data/**", "schema/**", "tests/regression/**"],
    "low": ["docs/**", "README.md"]
  },
  "release": { "version_files": ["CITATION.cff"] }
}
```

## One-time setup per product (owner)

1. Add the repository secret `ANTHROPIC_API_KEY` (optional) and set a monthly spend limit in the Anthropic console (suggested: 20 USD).
2. Switch the repository on in Zenodo (GitHub integration) to get a DOI per release.

## Tests

```bash
python -m pytest -q
```

## License

MIT
