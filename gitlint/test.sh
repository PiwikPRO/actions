#!/usr/bin/env bash

set -euo pipefail

action_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(mktemp -d "${TMPDIR:-/tmp}/gitlint-test.XXXXXX")"
trap 'rm -rf "$repo"' EXIT

git -C "$repo" init --quiet
git -C "$repo" config user.name "Gitlint Test"
git -C "$repo" config user.email "gitlint@example.com"

commit() {
  git -C "$repo" commit --allow-empty --quiet --message "$1"
}

commit "DEVOPS-9727 Initial change"
base_sha="$(git -C "$repo" rev-parse HEAD)"
commit "Squashed 'terraform/gatekeeper/' changes from ca90e4cc..32223d32"
commit "Merge commit '954873a7a5a1fd4e5357669c9b8168e820916f79' into DEVOPS-9727"
commit "feature/DEVOPS-9727 Complete gatekeeper update"
valid_head_sha="$(git -C "$repo" rev-parse HEAD)"
valid_range="$base_sha..$valid_head_sha"

(
  cd "$repo"
  gitlint --config "$action_dir/.gitlint" --commits "$valid_range"
)
(
  cd "$repo"
  bash "$action_dir/reject-placeholder-tickets.sh" "$valid_range"
)

commit "Invalid commit title"
if (
  cd "$repo"
  gitlint --config "$action_dir/.gitlint"
); then
  echo "Expected gitlint to reject a title without a ticket" >&2
  exit 1
fi

commit "INT-1337 Placeholder ticket"
(
  cd "$repo"
  gitlint --config "$action_dir/.gitlint"
)
if (
  cd "$repo"
  bash "$action_dir/reject-placeholder-tickets.sh"
); then
  echo "Expected placeholder ticket validation to fail" >&2
  exit 1
fi

echo "All gitlint tests passed"
