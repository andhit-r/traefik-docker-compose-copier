#!/usr/bin/env bash
# Matches CI job: compose-up
set -euo pipefail

SCENARIO=${1:?Usage: compose-scenario.sh <scenario>}
OUTDIR=/tmp/traefik-copier-compose-${SCENARIO}

echo "── compose-up: ${SCENARIO} ──"
rm -rf "$OUTDIR"

copier copy /workspace "$OUTDIR" \
    --defaults --overwrite --trust \
    --data-file "/workspace/tests/scenarios/${SCENARIO}.yml"

cd "$OUTDIR"

cleanup() {
    echo "cleaning up ${SCENARIO}..."
    docker compose down --volumes --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

docker compose up -d

echo "waiting 10 seconds for containers to settle..."
sleep 10

echo "=== docker compose ps ==="
docker compose ps
echo ""

running=$(docker compose ps --services --filter status=running)
echo "Running services: $running"

check_fail() {
    echo "=== logs on failure ==="
    docker compose logs --no-log-prefix
    exit 1
}

echo "$running" | grep -q "^proxy$" \
    || { echo "FAIL: proxy is not running"; check_fail; }

echo "$running" | grep -q "^dockersocket$" \
    || { echo "FAIL: dockersocket is not running"; check_fail; }

exited=$(docker compose ps --services --filter status=exited)
if [ -n "$exited" ]; then
    echo "FAIL: the following services exited: $exited"
    check_fail
fi

echo "compose-up ${SCENARIO}: PASSED"
echo ""
