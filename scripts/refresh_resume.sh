#!/bin/bash
set -euo pipefail

TOKEN_FILE="${RESUME_TOKEN_FILE:-/Users/mac/resume-kb/.refresh_token}"
URL="${RESUME_REFRESH_URL:-http://127.0.0.1:8092/api/resume/refresh}"

if [ ! -s "$TOKEN_FILE" ]; then
  echo "missing token file: $TOKEN_FILE" >&2
  exit 2
fi

TOKEN="$(cat "$TOKEN_FILE")"
BODY="$(curl -fsS -X POST -H "X-Resume-Token: $TOKEN" "$URL")"
echo "$BODY"
