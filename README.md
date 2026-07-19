# VaultKeeper

**Simple. Observable. Recoverable.**

VaultKeeper is a self-hosted, Linux-first backup orchestration platform built around transparent snapshots, reliable restores, and understandable infrastructure.

## Current release

`v0.1.0-alpha1` — **Foundation**

## Development stack

- Apache 2.4 reverse proxy
- FastAPI backend
- Vue 3 frontend
- MariaDB management database
- Redis
- Docker Compose

## Start the development stack

```bash
cp .env.example .env
docker compose up --build -d
```

Open `http://localhost:8080`.

API endpoints:

- `GET /api/v1/health`
- `GET /api/v1/version`

## Project status

VaultKeeper is under active construction. The first milestone establishes a runnable platform before snapshot and restore capabilities are added.
