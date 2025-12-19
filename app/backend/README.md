# CPS Growth Copilot Backend

FastAPI backend for CPS Growth Copilot.

## Setup

```bash
# Install dependencies
pip install -e .

# Set environment variables (copy from .env.example)
export POSTGRES_USER=cps_user
export POSTGRES_PASSWORD=cps_password
export POSTGRES_DB=cps_growth
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

## Run

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs

Visit http://localhost:8000/docs for interactive API documentation.

