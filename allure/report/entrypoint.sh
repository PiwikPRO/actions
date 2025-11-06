#!/usr/bin/env bash

set -euo pipefail

cd /github/workspace || {
  echo "Failed to change directory to /github/workspace"
  exit 1
}

unset JAVA_HOME

# Check if history exists (downloaded by workflow)
if [ -d "artifacts/allure/history" ] && [ "$(ls -A artifacts/allure/history 2>/dev/null)" ]; then
  echo "History found, will include in report"
else
  echo "No history found, generating report without history"
fi

# Generate Allure report with history (if available)
echo "Generating Allure report..."
if allure generate artifacts/allure -o artifacts/allure-report; then
  echo "Report generated successfully"
  if [ -d "artifacts/allure-report" ]; then
    echo "Report size: $(du -sh artifacts/allure-report | cut -f1)"
  fi
else
  echo "Report generation failed"
  exit 1
fi