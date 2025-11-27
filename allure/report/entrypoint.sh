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

ALLURE_RESULTS_DIR="${ARTIFACTS_PARENT}/allure"
ALLURE_REPORT_DIR="${ARTIFACTS_PARENT}/allure-report"

echo "Using artifacts parent directory: ${ARTIFACTS_PARENT}"
echo "Allure results location: ${ALLURE_RESULTS_DIR}"
echo "Report output location: ${ALLURE_REPORT_DIR}"

# Check if history exists (downloaded by workflow)
if [ -d "${ALLURE_RESULTS_DIR}/history" ] && [ "$(ls -A "${ALLURE_RESULTS_DIR}/history" 2>/dev/null)" ]; then
  echo "History found, will include in report"
else
  echo "No history found, generating report without history"
fi

# Generate Allure report with history (if available)
echo "Generating Allure report..."
if allure generate "${ALLURE_RESULTS_DIR}" -o "${ALLURE_REPORT_DIR}"; then
  echo "Report generated successfully"
  if [ -d "${ALLURE_REPORT_DIR}" ]; then
    REPORT_SIZE="$(du -sh "${ALLURE_REPORT_DIR}" | cut -f1)"
    echo "Report size: ${REPORT_SIZE}"
  fi
else
  echo "Report generation failed"
  exit 1
fi