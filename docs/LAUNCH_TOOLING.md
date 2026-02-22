# Launch Tooling

Lorelang launch checks are wired into local shortcuts and CI.

## Local Shortcuts

Use `make` from repo root:

```bash
make help
make test
make conformance
make validate-examples
make compile-matrix
make smoke
make launch-check
make dist-check
```

`make dist-check` requires `build` and `twine` Python packages to be installed.

## What `make launch-check` Runs

1. Full test suite
2. Language conformance tests
3. Validation across all example ontologies
4. Compile matrix across all built-in targets
5. End-to-end launch smoke workflow (`scripts/launch_smoke.sh`)

## CI Workflows

- `.github/workflows/ci.yml`
  - Runs on push/PR
  - Installs package
  - Runs `make launch-check`

- `.github/workflows/release-check.yml`
  - Runs on tags (`v*`) and manual dispatch
  - Installs packaging dependencies and runs `make dist-check`
  - Uploads `dist/*` artifacts

## Release Notes Template

Before tagging:

1. `make launch-check`
2. `make dist-check`
3. update version/changelog/release notes
4. tag and push (`vX.Y.Z`)
