#!/usr/bin/env bash

set -euo pipefail

range="${1:--1}"

while IFS= read -r title; do
  if [[ "$title" =~ ^((bugfix|feature)/)?([A-Z]+-[0-9]+)[[:space:]] ]]; then
    case "${BASH_REMATCH[3]}" in
      INT-1|INT-1337|INT-666|INTERNAL-1)
        echo "::error::If you have time to make a commit, you have time to create a ticket"
        exit 1
        ;;
    esac
  fi
done < <(git log "$range" --pretty=%s)
