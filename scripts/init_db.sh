#!/bin/bash
# Initialize database schema

set -e

echo "Waiting for PostgreSQL to be ready..."
sleep 5

PGUSER=${POSTGRES_USER:-cps_user}
PGPASSWORD=${POSTGRES_PASSWORD:-cps_password}
PGDATABASE=${POSTGRES_DB:-cps_growth}
PGHOST=${POSTGRES_HOST:-localhost}
PGPORT=${POSTGRES_PORT:-5432}

export PGPASSWORD

echo "Running database initialization..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f app/infra/postgres/init.sql

echo "✅ Database initialized successfully!"

