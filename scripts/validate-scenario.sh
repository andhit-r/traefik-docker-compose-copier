#!/usr/bin/env bash
# Matches CI job: validate-output
set -euo pipefail

SCENARIO=${1:?Usage: validate-scenario.sh <scenario>}
OUTDIR=/tmp/traefik-copier-validate-${SCENARIO}

echo "── validate-output: ${SCENARIO} ──"
rm -rf "$OUTDIR"

copier copy /workspace "$OUTDIR" \
    --defaults --overwrite --trust \
    --data-file "/workspace/tests/scenarios/${SCENARIO}.yml"

python3 - "$OUTDIR" <<'PYEOF'
import sys, yaml, pathlib

out = pathlib.Path(sys.argv[1])
failures = []

for name in ("docker-compose.yml", "traefik.yml", "config.yml"):
    path = out / name
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("root is not a mapping")
        print(f"  OK  {name}")
    except Exception as exc:
        print(f"FAIL  {name}: {exc}")
        failures.append(name)

if failures:
    sys.exit(1)
PYEOF

docker compose -f "$OUTDIR/docker-compose.yml" config -q
echo "docker compose config OK"
echo "validate-output ${SCENARIO}: PASSED"
echo ""
