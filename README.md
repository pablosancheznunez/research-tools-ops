# research-tools-ops

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23881629.svg)](https://doi.org/10.5281/zenodo.23881629)

Two reusable GitHub Actions workflows that keep open research software published and healthy with no credentials and no routine work.

| Workflow | Used by | Does |
| --- | --- | --- |
| `cran-watch.yml` | uxlearn, narrativecv, reproimage, visualbrief (every Wednesday) | Reads the package's public CRAN check results and fails if any platform reports ERROR, WARN or FAIL, so problems surface before CRAN's deadline. When CRAN publishes a new version, it creates the matching GitHub release, and Zenodo mints its DOI. |
| `auto-release.yml` | openresearchmetrics, ixd-lab (first day of each month) | If `main` changed and the tests pass, tags a patch release and publishes it; Zenodo mints its DOI. The version bump lives only on the tag, so `main` stays protected. |

Every project also runs its own CI on every change and weekly against the newest versions of its dependencies. GitHub emails the maintainer when any scheduled run fails; nothing else needs watching.

## Using it

```yaml
jobs:
  cran:
    uses: pablosancheznunez/research-tools-ops/.github/workflows/cran-watch.yml@main
    permissions:
      contents: write
    with:
      package: yourpackage
```

`auto-release.yml` reads the files to bump from `.maintenance.json`:

```json
{ "release": { "version_files": ["CITATION.cff", "DESCRIPTION"] } }
```

## Tests

```bash
python -m pytest -q
```

## Citation and license

See [`CITATION.cff`](CITATION.cff). MIT License.
