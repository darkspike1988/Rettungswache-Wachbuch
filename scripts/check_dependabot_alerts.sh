#!/usr/bin/env bash
# Fail-closed Dependabot alert gate.
#
# Exits non-zero when the state of open high/critical Dependabot alerts cannot
# be determined (auth, network, HTTP error, unexpected shape, invalid JSON) --
# never silently treating an API failure as "0 alerts". Requires an
# authenticated `gh` (GH_TOKEN).
#
# Exit codes:
#   0  queried successfully; no open high/critical alerts
#   1  queried successfully; at least one open high/critical alert
#   2  could not determine alert state (fail closed)
#
# Pagination: `gh api --paginate --slurp` follows Link headers and wraps every
# page into one outer JSON array, so >100 alerts are still counted.
set -euo pipefail

repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"

if ! output="$(gh api --paginate --slurp \
        -H 'Accept: application/vnd.github+json' \
        -H 'X-GitHub-Api-Version: 2022-11-28' \
        "repos/${repo}/dependabot/alerts?state=open&per_page=100" 2>&1)"; then
    echo "::error::Dependabot alert query failed (auth/network/API error). Failing closed." >&2
    echo "${output}" >&2
    exit 2
fi

count="$(printf '%s' "${output}" | python3 -c '
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception as exc:  # invalid JSON -> fail closed
    print("INVALID_JSON: " + str(exc))
    sys.exit(3)

# --slurp wraps pages as a list of page-lists; never accept unknown shapes.
if not isinstance(data, list) or not all(isinstance(page, list) for page in data):
    print("UNEXPECTED_PAGE_SHAPE")
    sys.exit(3)
items = [item for page in data for item in page]
count = 0
for alert in items:
    if not isinstance(alert, dict):
        print("UNEXPECTED_ALERT_SHAPE")
        sys.exit(3)
    advisory = alert.get("security_advisory")
    if not isinstance(advisory, dict) or advisory.get("severity") not in (
        "low", "moderate", "high", "critical"
    ):
        print("UNKNOWN_ADVISORY_SEVERITY")
        sys.exit(3)
    count += advisory["severity"] in ("high", "critical")
print(count)
')" || {
    echo "::error::Could not parse Dependabot response; failing closed." >&2
    exit 2
}

if [[ ! "${count}" =~ ^[0-9]+$ ]]; then
    echo "::error::Unexpected Dependabot parse result '${count}'; failing closed." >&2
    exit 2
fi

echo "Open high/critical Dependabot alerts: ${count}"
if [ "${count}" -gt 0 ]; then
    echo "::error::Open high/critical Dependabot alerts found: ${count}"
    echo "Please fix these vulnerabilities before merging."
    exit 1
fi

echo "No blocking high/critical Dependabot alerts."
