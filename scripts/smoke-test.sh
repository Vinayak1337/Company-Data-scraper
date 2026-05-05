#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000/api}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"
STAMP="$(date +%s)"
COMPANY_URL="https://example.com/job-scout-smoke-${STAMP}"
AUTH_HEADER=()
if [ -n "${BACKEND_API_TOKEN:-}" ]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${BACKEND_API_TOKEN}")
fi

json_field() {
  python3 -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

echo "Checking backend health at ${BACKEND_URL}/health"
curl -fsS "${BACKEND_URL}/health" >/dev/null

echo "Checking frontend at ${FRONTEND_URL}"
curl -fsS -I "${FRONTEND_URL}" >/dev/null

echo "Creating smoke-test company"
COMPANY_RESPONSE="$(
  curl -fsS -X POST "${BACKEND_URL}/companies" \
    "${AUTH_HEADER[@]}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Smoke Test ${STAMP}\",\"domain\":\"example.com\",\"careers_url\":\"${COMPANY_URL}\",\"priority_tier\":\"fallback\",\"is_active\":true}"
)"
COMPANY_ID="$(printf '%s' "${COMPANY_RESPONSE}" | json_field id)"
if [ -z "${COMPANY_ID}" ]; then
  echo "Could not parse smoke-test company id"
  exit 1
fi

echo "Checking crawl dry-run endpoint"
curl -fsS -X POST "${BACKEND_URL}/crawls/run-due" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true,"limit":1}' >/dev/null

echo "Checking profile onboarding endpoint"
curl -fsS "${AUTH_HEADER[@]}" "${BACKEND_URL}/profile" >/dev/null
if [ "${SMOKE_PROFILE_IMPORT:-0}" = "1" ]; then
  curl -fsS -X POST "${BACKEND_URL}/profile/import-resume" \
    "${AUTH_HEADER[@]}" \
    -H "Content-Type: application/json" \
    -d '{"resume_text":"Smoke Tester\nSkills: Python, Django, TypeScript\nExperience: Built developer tools."}' >/dev/null
fi

echo "Checking match-ranked jobs endpoint"
JOBS_RESPONSE="$(curl -fsS "${AUTH_HEADER[@]}" "${BACKEND_URL}/jobs?strong_fit_first=true")"
printf '%s' "${JOBS_RESPONSE}" | python3 -c 'import json, sys; data=json.load(sys.stdin); assert "results" in data'

echo "Checking V3 settings endpoints"
curl -fsS "${AUTH_HEADER[@]}" "${BACKEND_URL}/notifications/preferences" >/dev/null
curl -fsS "${AUTH_HEADER[@]}" "${BACKEND_URL}/agents/runtime" >/dev/null

echo "Cleaning smoke-test company ${COMPANY_ID}"
curl -fsS -X DELETE "${AUTH_HEADER[@]}" "${BACKEND_URL}/companies/${COMPANY_ID}" >/dev/null

echo "Smoke test passed."
