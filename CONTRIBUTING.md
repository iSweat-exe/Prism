# Contributing

## Branches

- `master` — stable, production-ready
- `dev` — active development, target this branch for all pull requests
- feature branches follow the pattern `feature/short-description`
- fix branches follow the pattern `fix/short-description`

## Workflow

1. Fork the repository and create your branch from `dev`
2. Make your changes
3. Run lint and tests before pushing

```bash
ruff check .
pytest
```

4. Open a pull request targeting `dev` with a clear description of what changed and why

## Commit messages

Keep them short and in lowercase, written in the imperative form.

```
add disk io rate to sampler
fix latency worker not resetting on timeout
remove unused import in network router
```

## Code style

The project uses Ruff for linting. A passing `ruff check .` is required before any merge.

## Reporting issues

Open a GitHub issue with a description of the problem, the steps to reproduce it, and the relevant log output from `pm2 logs prism-api`.