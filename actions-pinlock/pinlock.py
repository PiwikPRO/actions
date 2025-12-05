#!/usr/bin/env python3
"""
Pinlock - Automated GitHub Actions version updater.

Scans workflow files for GitHub Actions usage and updates them to match
approved versions defined in a config file (dependactionbot.json).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Regex to match: uses: owner/repo@version
USES_PATTERN = re.compile(
    r"^(\s*uses:\s+)([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)@([a-zA-Z0-9.]+)(.*)$", re.MULTILINE
)


class Pinlock:
    def __init__(
        self,
        repo_root: Path,
        config_file: Path,
        dry_run: bool = False,
        pr: bool = False,
    ):
        self.repo_root = repo_root
        self.config_file = config_file
        self.dry_run = dry_run
        self.pr = pr
        self.workflows_dir = repo_root / ".github" / "workflows"

    def load_expected_versions(self) -> Dict[str, str]:
        """Load expected action versions from config file."""
        if not self.config_file.exists():
            print(f"❌ Config file not found: {self.config_file}")
            sys.exit(1)

        with open(self.config_file) as f:
            config = json.load(f)

        # Extract version strings from nested dict
        actions_config = config.get("actions", {})
        return {
            action_name: action_data["version"]
            for action_name, action_data in actions_config.items()
        }

    def scan_workflows(self) -> List[Path]:
        """Find all workflow YAML files."""
        if not self.workflows_dir.exists():
            print(f"❌ Workflows directory not found: {self.workflows_dir}")
            sys.exit(1)

        yaml_files = list(self.workflows_dir.glob("*.yml")) + list(
            self.workflows_dir.glob("*.yaml")
        )

        return sorted(yaml_files)

    def extract_actions(self, content: str) -> List[Tuple[str, str]]:
        """Extract all action names and versions from workflow content."""
        actions = []
        for match in USES_PATTERN.finditer(content):
            action_name = match.group(2)
            version = match.group(3)
            actions.append((action_name, version))
        return actions

    def find_mismatches(
        self, workflow_files: List[Path], expected_versions: Dict[str, str]
    ) -> Dict[Path, List[Tuple[str, str, str]]]:
        """
        Find version mismatches between workflows and expected versions.

        Returns:
            Dict mapping file paths to list of (action_name, current_version, expected_version)
        """
        mismatches = {}

        for filepath in workflow_files:
            content = filepath.read_text()
            actions = self.extract_actions(content)

            file_mismatches = []
            for action_name, current_version in actions:
                if action_name in expected_versions:
                    expected_version = expected_versions[action_name]
                    if current_version != expected_version:
                        file_mismatches.append(
                            (action_name, current_version, expected_version)
                        )

            if file_mismatches:
                mismatches[filepath] = file_mismatches

        return mismatches

    def update_file(self, filepath: Path, updates: List[Tuple[str, str, str]]) -> str:
        """
        Update action versions in a workflow file.

        Args:
            filepath: Path to workflow file
            updates: List of (action_name, old_version, new_version)

        Returns:
            Updated file content
        """
        content = filepath.read_text()

        for action_name, old_version, new_version in updates:
            # Create a pattern that matches this specific action and version
            pattern = re.compile(
                rf"^(\s*uses:\s+{re.escape(action_name)})@{re.escape(old_version)}(.*)$",
                re.MULTILINE,
            )
            content = pattern.sub(rf"\1@{new_version}\2", content)

        return content

    def create_branch_name(self) -> str:
        """Generate a branch name with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"actions-pinlock/update-actions-{timestamp}"

    def create_pr_body(self, mismatches: Dict[Path, List[Tuple[str, str, str]]]) -> str:
        """Generate PR description."""
        lines = [
            "🔒 **Pinlock: Update GitHub Actions**",
            "",
            "The following actions have been updated to their approved versions:",
            "",
        ]

        # Collect all unique updates
        all_updates = {}
        for updates in mismatches.values():
            for action_name, old_version, new_version in updates:
                all_updates[action_name] = (old_version, new_version)

        for action_name in sorted(all_updates.keys()):
            old_version, new_version = all_updates[action_name]
            # Show short version (first 7 chars for commit hashes)
            old_short = old_version[:7] if len(old_version) > 10 else old_version
            new_short = new_version[:7] if len(new_version) > 10 else new_version
            lines.append(f"- `{action_name}`: `{old_short}...` → `{new_short}...`")

        lines.extend(["", "---", "*Generated by Pinlock*"])

        return "\n".join(lines)

    def run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run a git command."""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Git command failed: git {' '.join(args)}")
            print(f"Error: {result.stderr}")
            sys.exit(1)
        return result

    def run(self):
        """Main execution logic."""
        print("🔒 Pinlock starting...")

        # Load configuration
        expected_versions = self.load_expected_versions()
        print(f"📋 Loaded {len(expected_versions)} expected action versions")

        # Scan workflows
        workflow_files = self.scan_workflows()
        print(f"🔍 Found {len(workflow_files)} workflow files")

        # Find mismatches
        mismatches = self.find_mismatches(workflow_files, expected_versions)

        if not mismatches:
            print("✅ All actions are up to date!")
            return

        # Display mismatches
        print(f"\n⚠️  Found version mismatches in {len(mismatches)} file(s):")
        for filepath, updates in mismatches.items():
            rel_path = filepath.relative_to(self.repo_root)
            print(f"\n  📄 {rel_path}")
            for action_name, old_version, new_version in updates:
                old_short = old_version[:7] if len(old_version) > 10 else old_version
                new_short = new_version[:7] if len(new_version) > 10 else new_version
                print(f"    • {action_name}: {old_short}... → {new_short}...")

        if self.dry_run:
            print("\n🔍 Dry-run mode: No changes will be made")
            return

        # Create branch
        branch_name = self.create_branch_name()
        print(f"\n🌿 Creating branch: {branch_name}")
        self.run_git_command(["checkout", "-b", branch_name])

        # Update files
        print("\n📝 Updating workflow files...")
        for filepath, updates in mismatches.items():
            updated_content = self.update_file(filepath, updates)
            filepath.write_text(updated_content)
            rel_path = filepath.relative_to(self.repo_root)
            print(f"  ✓ Updated {rel_path}")
            self.run_git_command(["add", str(filepath)])

        # Commit changes
        commit_msg = "chore: update GitHub Actions to approved versions"
        print("\n💾 Committing changes...")
        self.run_git_command(["commit", "-m", commit_msg])

        # Push branch
        print("\n⬆️  Pushing branch to origin...")
        self.run_git_command(["push", "-u", "origin", branch_name])

        # Create PR
        if self.pr:
            print("\n🔀 Creating pull request...")
            pr_body = self.create_pr_body(mismatches)
            pr_title = "chore: update GitHub Actions to approved versions"

            result = subprocess.run(
                ["gh", "pr", "create", "--title", pr_title, "--body", pr_body],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Pull request created successfully!")
                print(result.stdout.strip())
            else:
                print("⚠️  Failed to create PR (you may need to install gh CLI)")
                print(f"   Branch pushed: {branch_name}")
                print(
                    f"   Create PR manually at: https://github.com/your-org/your-repo/compare/{branch_name}"
                )
        else:
            print(f"\n✅ Changes pushed to branch: {branch_name}")
            print("   Create PR manually if needed")


def main():
    parser = argparse.ArgumentParser(
        description="Update GitHub Actions to approved versions"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (default: dependactionbot.json in repo root)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root path (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them",
    )
    parser.add_argument(
        "--pr",
        action="store_true",
        help="Create a pull request with the changes",
    )

    args = parser.parse_args()

    # Resolve config file
    config_file = args.config or (args.repo / "dependactionbot.json")

    pinlock = Pinlock(
        repo_root=args.repo,
        config_file=config_file,
        dry_run=args.dry_run,
        pr=args.pr,
    )
    pinlock.run()


if __name__ == "__main__":
    main()
