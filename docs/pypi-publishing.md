# Publishing to PyPI

One-time setup before the first release.

## 1. PyPI Trusted Publisher

1. Open [pypi.org](https://pypi.org) → Account settings → **Publishing** → **Add a new pending publisher**.
2. Fill in:

   | Field | Value |
   |-------|-------|
   | PyPI project name | `yandex-messenger-bot` |
   | Owner | `arielen` |
   | Repository name | `yandex-messenger-bot` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. Save. The publisher becomes active after the first successful publish.

No API token is required — [`.github/workflows/release.yml`](../.github/workflows/release.yml) uses OIDC (`id-token: write`).

## 2. GitHub environment

1. Repository **Settings** → **Environments** → **New environment**.
2. Name: `pypi` (must match the workflow `environment.name`).
3. Optional: restrict deployments to the `master` branch and require reviewers.

## 3. Release a version

```bash
# Bump version in yandex_messenger_bot/_meta.py, commit, then:
git tag v0.1.0
git push origin v0.1.0
```

The [Release to PyPI](../.github/workflows/release.yml) workflow will run tests, build the package, and publish to PyPI.

Tag must match the package version: `vX.Y.Z` ↔ `__version__` in `_meta.py`.

## Optional: TestPyPI

Repeat Trusted Publisher setup on [test.pypi.org](https://test.pypi.org) with the same GitHub repository settings, then publish manually:

```bash
uv build
uv publish --index https://test.pypi.org/legacy/ dist/*
```
