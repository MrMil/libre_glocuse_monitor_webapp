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

## Type checking

```bash
uv run mypy app/
```
