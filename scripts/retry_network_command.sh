#!/bin/bash
# Retry only failures whose output identifies a transient download/network error.
set -euo pipefail
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT
for ATTEMPT in 1 2 3; do
  set +e
  "$@" 2>&1 | tee "$LOG_FILE"
  COMMAND_STATUS=${PIPESTATUS[0]}
  set -e
  if [ "$COMMAND_STATUS" -eq 0 ]; then
    exit 0
  fi
  if [ "$ATTEMPT" -eq 3 ] || ! grep -Eiq 'status code (408|429|500|502|503|504)|returned error: (408|429|500|502|503|504)|ECONNRESET|ETIMEDOUT|EAI_AGAIN|connection reset|connection timed out|TLS handshake timeout' "$LOG_FILE"; then
    exit "$COMMAND_STATUS"
  fi
  echo "Transient network failure; retrying in $((ATTEMPT * 5)) seconds ($ATTEMPT/3)..." >&2
  sleep "$((ATTEMPT * 5))"
done
