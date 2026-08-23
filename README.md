# Adaptive Technical Debt Discovery Form

Local FastAPI application that conducts an adaptive discovery interview using **Ollama**, constrained by a deterministic schema. Converts company information into a reviewed technical-debt and source-security **assessment plan** with downloadable documents.

## Features

- **Business Details** — industry, size, compliance, tooling, risk tolerance (dropdowns where applicable)
- **Assessment objectives** — goals, audiences, release blockers
- **Application inventory** — register systems with owners, repos, data, criticality
- **Adaptive interview** — Ollama-generated questions with offline schema fallback
- **Document-style plan** — readable report view plus raw YAML
- **Approve & export** — PDF, Excel, and JSON saved to `data/documents/{session_id}/`
- **Retrieval key** — reusable key for returning users to CRUD their submission (shown in popup and PDF)
- **Admin panel** — login to list sessions, edit data, regenerate documents

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) (optional — schema fallback if unavailable)

```bash
ollama pull deepseek-v4-flash:cloud
ollama serve
```

## Setup

```bash
cd form-builder-TDD-discovery
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit SECRET_KEY and admin password
```

## Environment (`.env`)

```env
ENVIRONMENT=development
SECRET_KEY=change-me-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
# Production: set ENVIRONMENT=production, a 32+ char SECRET_KEY, and ADMIN_PASSWORD_HASH
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=deepseek-v4-flash:cloud
```

Generate a bcrypt admin password hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
```

## Security

- CSRF protection on all POST forms
- Rate limiting on admin login and retrieve (5/min and 10/min per IP)
- Security headers (CSP, frame deny, nosniff, referrer policy)
- Bcrypt admin passwords in production (`ADMIN_PASSWORD_HASH`)
- Path traversal guards on document downloads
- Startup validation refuses weak defaults when `ENVIRONMENT=production`

Out of scope for this app: SQLite encryption (use filesystem permissions + HTTPS), edge WAF/DDoS (use a reverse proxy in production).

## Run

```bash
uvicorn app.main:app --reload
```

- **New session:** http://127.0.0.1:8000
- **Retrieve submission:** http://127.0.0.1:8000/retrieve
- **Admin:** http://127.0.0.1:8000/admin/login

## Public flow

```
Business Details → Objectives → Applications → Interview → Plan document → Approve → PDF/Excel/JSON + save retrieval key
```

Returning users enter their key at `/retrieve` to continue editing.

## Data

- SQLite: `data/sessions.db`
- Exported documents: `data/documents/{session_id}/`

## Test

```bash
pytest -v
```

Tests mock Ollama; no local model required for CI.
