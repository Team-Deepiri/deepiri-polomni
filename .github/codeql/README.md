# CodeQL Setup for deepiri-omnifold repository

This folder contains the CodeQL configuration for repository-level security scanning.

## What each file does

- `.github/workflows/codeql.yml`
  - Defines when scans run and how GitHub Actions executes CodeQL.
- `.github/codeql/codeql-config.yml`
  - Defines what folders to include and ignore during analysis.

## Workflow breakdown (`.github/workflows/codeql.yml`)

### `name: CodeQL`
The display name in the Actions tab.

### `on.pull_request.branches` and `on.push.branches`
```yaml
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main, dev]
```
Runs scans when PRs target `main` or `dev`, and when commits are pushed to `main` or `dev`.

### `permissions`
```yaml
permissions:
  actions: read
  contents: read
  security-events: write
```
Uses least-privilege permissions. `security-events: write` is required so CodeQL can upload findings.

### `strategy.matrix.language`
```yaml
language: [python]
```
Runs Python analysis for omnifold_core, omnifold_neural, omnifold_observatory, omnifold_cli, and related packages.

### Checkout step
```yaml
with:
  fetch-depth: 0
```
- `fetch-depth: 0` keeps full git history (safe default for analysis and troubleshooting).

### Initialize CodeQL
```yaml
uses: github/codeql-action/init@v3
```
Starts the CodeQL engine and loads `.github/codeql/codeql-config.yml`.

### Analyze
```yaml
uses: github/codeql-action/analyze@v3
```
Executes queries and uploads results to GitHub Security.

## Config breakdown (`.github/codeql/codeql-config.yml`)

### `paths-ignore`
Generated, experiment notebooks, docs, and environment files excluded to reduce noise and run time.

## Best practices

1. Keep trigger scope intentional — use branch filters (`main`, `dev`) to control cost and noise.
2. Keep language list explicit — Python only for this research framework.
3. Exclude generated/vendor artifacts — caches, docs, experiments, and virtualenv paths in `paths-ignore`.
4. Pin to stable major action versions — `@v3` for CodeQL actions.
5. Review alerts regularly — triage high/critical findings first.

## Maintenance examples

### Exclude another generated folder
Add a glob to `paths-ignore`, for example:
```yaml
- '**/generated/**'
```
