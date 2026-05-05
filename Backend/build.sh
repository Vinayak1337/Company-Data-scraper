#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi
npm run build:css
python manage.py collectstatic --no-input
