#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT}/src"

tmpdir="$(mktemp -d /tmp/lore-launch-smoke-XXXXXX)"
trap 'rm -rf "${tmpdir}"' EXIT

ontology_dir="${tmpdir}/smoke-ontology"

python3 -m lore.cli setup "${ontology_dir}" --name smoke-ontology --domain "Launch Smoke" >/dev/null

cat > "${tmpdir}/meeting.txt" <<'TXT'
Facilitator: Client has 3 teams and 2 blockers.
Facilitator: We think security review is likely gating launch.
Facilitator: It is important to finish SSO before pilot.
Facilitator: Historically this issue delayed onboarding.
TXT

python3 -m lore.cli ingest transcript "${ontology_dir}" \
  --input "${tmpdir}/meeting.txt" \
  --about DomainObject \
  --date 2026-02-22 >/dev/null

cat > "${tmpdir}/memory.json" <<'JSON'
[{"memory":"Prior launch had same security blocker.","tags":["precedent"]}]
JSON

python3 -m lore.cli ingest memory "${ontology_dir}" \
  --adapter mem0 \
  --input "${tmpdir}/memory.json" \
  --about DomainObject \
  --date 2026-02-22 >/dev/null

python3 -m lore.cli validate "${ontology_dir}" >/dev/null
python3 -m lore.cli curate "${ontology_dir}" --dry-run >/dev/null
python3 -m lore.cli compile "${ontology_dir}" -t agent --view "Domain Curator" >/dev/null
python3 -m lore.cli evolve "${ontology_dir}" >/dev/null || true

if ls "${ontology_dir}/proposals"/*.lore >/dev/null 2>&1; then
  python3 -m lore.cli review "${ontology_dir}/proposals" \
    --decision accept \
    --reviewer launch-smoke-check >/dev/null
fi

python3 -m lore.cli validate "${ontology_dir}" >/dev/null
echo "launch smoke passed"
