# Sugar Monitor

A web app that displays your current glucose level from LibreLinkUp.

## Setup

1. Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your LibreLinkUp email and password. Set `LIBRE_REGION` to your region (`US`, `EU`, `EU2`, `DE`, `FR`, `AU`, `CA`, `JP`, `AP`, `AE`, `LA`).

2. Install dependencies:

```bash
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000.

## Tests

Install test dependencies:

```bash
uv sync          # includes Python dev dependencies (pytest, pytest-cov, etc.)
npm install      # installs Vitest for JavaScript tests
```

Python tests (with verbose output and coverage):

```bash
uv run pytest -v --cov=app --cov-report=term-missing
```

JavaScript tests (with verbose output):

```bash
npx vitest run --reporter=verbose
```

## Type checking

```bash
uv run mypy app/
```
