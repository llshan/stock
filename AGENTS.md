# Repository Guidelines

## Project Structure & Module Organization
- Source: `stock_analysis/` (subpackages: `data/`, `analysis/`, `trading/`, `cli/`, `utils/`)
- Tests: `tests/` (e.g., `tests/trading/test_*.py`)
- Docs: `docs/` (design notes, migration guides)
- Data & DB: `database/stock_data.db` (SQLite), sample `transactions.txt`, outputs in `result/`
- Scripts: `import_transactions.py`, `load_transactions.py`

## Build, Test, and Development Commands
- Install (dev): `python -m venv venv && source venv/bin/activate && pip install -e "."[dev]`
- CLI entry points (after install): `stock-data`, `stock-analyze`, `stock-db`, `financial-metrics`, `stock-trading`
  - Example: `stock-trading positions --user-id u1`
- Run tests: `pytest -q` or `pytest tests/trading -q`
- Lint & format: `black . && isort . && flake8 .`
- Type-check: `mypy .`

## Coding Style & Naming Conventions
- Python 3.8+; PEP 8 with line length 100.
- Formatting: Black; Imports: isort (Black profile); Lint: Flake8.
- Types: add annotations; `mypy` is strict (`disallow_untyped_defs = true`).
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, modules in `snake_case`.

## Testing Guidelines
- Framework: `pytest` with test files under `tests/` named `test_*.py`.
- Write focused unit tests for new services, calculators, and CLI behaviors.
- Prefer deterministic data; use in-memory DB when possible (`TESTING_CONFIG`).
- Run: `pytest -q`; for a full sweep: `pytest tests -q`.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise scope (e.g., "Add lot-level PnL calculator").
- Before opening a PR: ensure `pytest -q`, `black`, `isort`, `flake8`, and `mypy` all pass.
- PRs should include: clear description, rationale, screenshots or CLI output if UI/CLI changes, and references to related issues.
- Update docs in `docs/` and README examples when behavior changes.

## Security & Configuration Tips
- Do not commit secrets or tokens. Configure API keys via env vars.
- DB path can be overridden with `DATA_SERVICE_DB_PATH`; default is `database/stock_data.db`.
- Useful env vars: `WATCHLIST`, `DATA_SERVICE_*` (see `stock_analysis/data/config.py`).
