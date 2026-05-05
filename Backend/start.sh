#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Installing Python dependencies..."
.venv/bin/pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
  if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
  fi

  echo "Building Tailwind CSS..."
  npm run build:css
else
  echo "npm is required to build Tailwind CSS but was not found."
  exit 1
fi

echo "Applying database migrations..."
.venv/bin/python manage.py migrate --no-input

echo "Seeding default companies..."
.venv/bin/python manage.py seed_companies

echo "Starting server at http://${HOST}:${PORT}/"
.venv/bin/python manage.py runserver "${HOST}:${PORT}"
