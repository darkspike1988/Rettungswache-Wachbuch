#!/bin/sh
set -eu

usage() {
    echo "Aufruf: ./scripts/update.sh --apply-requested" >&2
    exit 2
}

[ "${1:-}" = "--apply-requested" ] || usage
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
env_file="$repo_root/.env"
[ -f "$env_file" ] || { echo "Fehlt: $env_file" >&2; exit 1; }

for required_command in docker git python3; do
    command -v "$required_command" >/dev/null 2>&1 || {
        echo "Fehlendes Programm: $required_command" >&2
        exit 1
    }
done

cd "$repo_root"
git_dir="$(git rev-parse --git-dir 2>/dev/null || true)"
[ -n "$git_dir" ] || { echo "Das Update muss in einem Git-Checkout laufen." >&2; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || {
    echo "Abbruch: Der Checkout enthält lokale Änderungen." >&2
    exit 1
}

repository="$(awk -F= '$1 == "UPDATE_REPOSITORY" { print $2; exit }' "$env_file")"
repository="${repository:-Darkspike1988/Rettungswache-Wachbuch}"
case "$repository" in
    *[!A-Za-z0-9_.\/-]*|*/*/*|/*|*/|"") echo "Ungültiges UPDATE_REPOSITORY." >&2; exit 1 ;;
esac
remote_url="$(git remote get-url origin)"
remote_lower="$(printf '%s' "$remote_url" | tr '[:upper:]' '[:lower:]')"
expected_lower="$(printf 'https://github.com/%s.git' "$repository" | tr '[:upper:]' '[:lower:]')"
[ "$remote_lower" = "$expected_lower" ] || {
    echo "Abbruch: origin stimmt nicht mit UPDATE_REPOSITORY überein." >&2
    exit 1
}

request_id=""
request_finished=false
rollback_image=""
candidate_image=""
worktree_dir=""

finish_failed() {
    exit_code=$?
    trap - EXIT HUP INT TERM
    if [ -n "$rollback_image" ] && docker image inspect "$rollback_image" >/dev/null 2>&1; then
        docker image tag "$rollback_image" rettungswache-wachbuch:local >/dev/null 2>&1 || true
        docker compose up -d --no-build --force-recreate --wait --wait-timeout 90 \
            web feed-worker push-worker >/dev/null 2>&1 || true
    fi
    if [ -n "$request_id" ] && [ "$request_finished" = "false" ]; then
        docker compose exec -T web python manage.py manage_update_requests \
            --finish "$request_id" --status failed \
            --message "Update-Runner abgebrochen; Logs auf dem Host prüfen." >/dev/null 2>&1 || true
    fi
    if [ -n "$worktree_dir" ] && [ -d "$worktree_dir" ]; then
        case "$worktree_dir" in
            "${TMPDIR:-/tmp}"/wachbuch-update.*) git worktree remove --force "$worktree_dir" >/dev/null 2>&1 || true ;;
        esac
    fi
    exit "$exit_code"
}
trap finish_failed EXIT HUP INT TERM

claim_json="$(docker compose exec -T web python manage.py manage_update_requests --claim)"
request_id="$(printf '%s' "$claim_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); item=data.get("request"); print("" if item is None else item["id"])')"
[ -n "$request_id" ] || {
    request_finished=true
    trap - EXIT HUP INT TERM
    echo "Kein offener Updateauftrag."
    exit 0
}
target_version="$(printf '%s' "$claim_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["request"]["target_version"])')"
case "$target_version" in
    *[!0-9A-Za-z.-]*|"") echo "Ungültige Zielversion im Updateauftrag." >&2; exit 1 ;;
esac

git fetch --prune origin main --tags
tag_ref=""
for candidate_tag in "v$target_version" "$target_version"; do
    if git show-ref --verify --quiet "refs/tags/$candidate_tag"; then
        tag_ref="refs/tags/$candidate_tag"
        break
    fi
done
[ -n "$tag_ref" ] || { echo "Release-Tag für $target_version fehlt." >&2; exit 1; }

require_signature="$(awk -F= '$1 == "UPDATE_REQUIRE_SIGNED_TAG" { print tolower($2); exit }' "$env_file")"
require_signature="${require_signature:-true}"
if [ "$require_signature" = "true" ]; then
    git verify-tag "${tag_ref#refs/tags/}"
fi
current_commit="$(git rev-parse HEAD)"
target_commit="$(git rev-list -n 1 "$tag_ref")"
git merge-base --is-ancestor "$current_commit" "$target_commit" || {
    echo "Abbruch: Das Release ist kein Fast-Forward des installierten Stands." >&2
    exit 1
}

worktree_dir="$(mktemp -d "${TMPDIR:-/tmp}/wachbuch-update.XXXXXX")"
git worktree add --detach "$worktree_dir" "$target_commit"
candidate_image="rettungswache-wachbuch:candidate-$request_id"
docker build --tag "$candidate_image" "$worktree_dir"

docker compose exec -T backup /bin/sh /backup/backup-loop.sh --once
rollback_image="rettungswache-wachbuch:rollback-$request_id"
docker image tag rettungswache-wachbuch:local "$rollback_image"
docker image tag "$candidate_image" rettungswache-wachbuch:local

docker compose run --rm --no-deps migrate
docker compose up -d --no-build --force-recreate --wait --wait-timeout 90 \
    web feed-worker push-worker

git merge --ff-only "$target_commit"
docker compose exec -T web python manage.py manage_update_requests \
    --finish "$request_id" --status succeeded \
    --message "Update und Healthcheck erfolgreich."
request_finished=true
git worktree remove --force "$worktree_dir"
worktree_dir=""
docker image rm "$rollback_image" "$candidate_image" >/dev/null 2>&1 || true
trap - EXIT HUP INT TERM
echo "Update auf $target_version erfolgreich abgeschlossen."
