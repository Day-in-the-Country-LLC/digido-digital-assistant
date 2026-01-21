# Python Orchestration Service Guidelines

## Dependency Management
- Use `uv` for dependency management.
- Run `uv sync` to reproduce the environment.
- Regenerate `uv.lock` when dependencies change.

## Testing
- Execute `pytest -q` and fix failures.
- Add or update unit tests for new or changed behavior.
- Parameterize tests when it reduces repetition.

## Style
- Follow PEP 8.
- Use ruff for linting and formatting.
- Add logging for key operations and background jobs.
- Add docstrings for public functions.
- Keep code style consistent with surrounding files.

## Pull Request
- Describe what changed and why.
- Include test results in the PR description.
