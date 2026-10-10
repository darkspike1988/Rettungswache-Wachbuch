#!/usr/bin/env bash
# Unit tests for scripts/check_dependabot_alerts.sh using a mocked `gh`.
# Proves fail-closed behaviour (auth/network/HTTP error, invalid JSON,
# unexpected shape) and multi-page counting -- all offline, no secrets.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gate="${GATE_UNDER_TEST:-${here}/../check_dependabot_alerts.sh}"
work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

pass=0
fail=0

run_case() { # name expected_exit mock_exit payload
    local name="$1" expected="$2" mock_exit="$3" payload="$4"
    printf '%s' "${payload}" > "${work}/payload"
    cat > "${work}/gh" <<EOF
#!/usr/bin/env bash
cat >/dev/null  # consume stdin if any
if [ "${mock_exit}" != "0" ]; then
    echo "gh: mock API failure (auth/network/HTTP)" >&2
    exit ${mock_exit}
fi
cat "${work}/payload"
EOF
    chmod +x "${work}/gh"
    set +e
    PATH="${work}:${PATH}" GITHUB_REPOSITORY="org/repo" \
        bash "${gate}" > "${work}/out" 2>&1
    local rc=$?
    set -e
    if [ "${rc}" -eq "${expected}" ]; then
        echo "PASS: ${name} (exit ${rc})"
        pass=$((pass + 1))
    else
        echo "FAIL: ${name} expected exit ${expected}, got ${rc}"
        sed 's/^/    /' "${work}/out"
        fail=$((fail + 1))
    fi
}

# POS: no open alerts at all.
run_case "no_alerts_pass" 0 0 '[[]]'
# POS: only low/moderate alerts -> not blocking.
run_case "low_medium_pass" 0 0 \
    '[[{"security_advisory":{"severity":"moderate"}},{"security_advisory":{"severity":"low"}}]]'
# NEG: one high alert -> blocking.
run_case "one_high_blocks" 1 0 \
    '[[{"security_advisory":{"severity":"high"}}]]'
# NEG: one critical alert -> blocking.
run_case "one_critical_blocks" 1 0 \
    '[[{"security_advisory":{"severity":"critical"}}]]'
# NEG + pagination: blocking alert only on the second page must be counted.
run_case "paginated_second_page_blocks" 1 0 \
    '[[{"security_advisory":{"severity":"low"}}],[{"security_advisory":{"severity":"critical"}}]]'
# FAIL-CLOSED: gh auth/network/HTTP error must NOT be treated as "0".
run_case "api_error_fails_closed" 2 1 ''
# FAIL-CLOSED: invalid JSON body.
run_case "invalid_json_fails_closed" 2 0 'not json at all'
# FAIL-CLOSED: unexpected shape (API error envelope).
run_case "unexpected_shape_fails_closed" 2 0 '{"message":"Not Found","status":"404"}'
# FAIL-CLOSED: HTTP 403 (rate limit) surfaces as gh failure.
run_case "http_403_fails_closed" 2 1 ''

# Unknown/missing advisory severity and malformed pagination must fail closed.
run_case "missing_advisory_fails_closed" 2 0 '[[{}]]'
run_case "null_advisory_fails_closed" 2 0 '[[{"security_advisory":null}]]'
run_case "unknown_severity_fails_closed" 2 0 '[[{"security_advisory":{"severity":"unknown"}}]]'
run_case "mixed_page_shapes_fails_closed" 2 0 '[[],{"error":"broken page"}]'

echo "-----------------------------------------"
echo "mock gate tests: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
