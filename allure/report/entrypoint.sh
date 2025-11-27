#!/usr/bin/env bash

set -euo pipefail

cd /github/workspace || {
  echo "Failed to change directory to /github/workspace"
  exit 1
}

unset JAVA_HOME

# Get path to parent artifacts directory from input or use default
ARTIFACTS_PARENT="${INPUT_PATH_TO_ARTIFACTS:-artifacts/}"
# Remove trailing slash if present
ARTIFACTS_PARENT="${ARTIFACTS_PARENT%/}"

echo "Using artifacts parent directory: ${ARTIFACTS_PARENT}"
echo "Allure results location: ${ARTIFACTS_PARENT}/allure"
echo "Report output location: ${ARTIFACTS_PARENT}/allure-report"

# Check if history exists (downloaded by workflow)
if [ -d "${ARTIFACTS_PARENT}/allure/history" ] && [ "$(ls -A ${ARTIFACTS_PARENT}/allure/history 2>/dev/null)" ]; then
  echo "History found, will include in report"
else
  echo "No history found, generating report without history"
fi

# Generate Allure report with history (if available)
echo "Generating Allure report..."
if allure generate "${ARTIFACTS_PARENT}/allure" -o "${ARTIFACTS_PARENT}/allure-report"; then
  echo "Report generated successfully"
  if [ -d "${ARTIFACTS_PARENT}/allure-report" ]; then
    echo "Report size: $(du -sh ${ARTIFACTS_PARENT}/allure-report | cut -f1)"
  fi
else
  echo "Report generation failed"
  exit 1
fi