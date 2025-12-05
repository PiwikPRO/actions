# Actions Pinlock

Automated GitHub Actions version updater that ensures workflow files use approved action versions.

## Overview

Pinlock scans GitHub workflow files for action usage and automatically updates them to match approved versions defined in a configuration file. This helps maintain consistency and security across your workflows.

## Features

- 🔍 Scans all workflow files in `.github/workflows/`
- 🔒 Pins actions to specific versions (commit SHA, tags, etc.)
- 🤖 Automatically creates PRs with version updates
- 🧪 Dry-run mode to preview changes
- 📦 Zero external dependencies (Python stdlib only)
- 🎯 Regex-based for maximum compatibility

## Usage

### As an Action

Use Pinlock as a GitHub Action in your workflows:

```yaml
- name: Run Pinlock
  uses: your-org/actions/pinlock@v1
  with:
    dry-run: false
```

### As a Reusable Workflow

Use the provided reusable workflow for automated scheduling in your repository. Create `.github/workflows/pinlock.yaml`:

```yaml
name: Pinlock

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC

jobs:
  pinlock:
    uses: your-org/actions/.github/workflows/pinlock.yaml@main
```

That's it! The reusable workflow automatically:
- Checks out your repository
- Downloads the [config](./dependactionbot.json) with action/hash commit mapping.
- Checks actions versions in your workflows
- Creates a PR with any necessary updates

## Configuration

Pinlock uses a `dependactionbot.json` [file](./dependactionbot.json). This serves as the single source of truth for all repositories.

```json
{
  "actions": {
    "actions/checkout": {
      "version": "8e8c483db84b4bee98b60c0593521ed34d9990e8"
    },
    "astral-sh/setup-uv": {
      "version": "38f3f104447c67c051c4a08e39b64a148898af3a"
    },
    "actions/setup-python": {
      "version": "0b93645e9fea7318ecaed2b359559ac225c90a2b"
    }
  }
}
```

All consumer repositories should use this single config file - no need to maintain separate copies.

### Version Formats

Pinlock supports multiple version formats:
- **Full commit SHA**: `8e8c483db84b4bee98b60c0593521ed34d9990e8`
- **Short commit SHA**: `8e8c483`
- **Tags**: `v4`, `v4.0.0`, `latest`

## Inputs

### `config-path`
- **Description**: Path to configuration file (relative to repo root)
- **Required**: false
- **Default**: `dependactionbot.json`

### `dry-run`
- **Description**: Preview changes without making them
- **Required**: false
- **Default**: `false`

### `no-pr`
- **Description**: Push branch but don't create PR
- **Required**: false
- **Default**: `false`

## How It Works

1. Loads expected action versions from config file
2. Scans all `.github/workflows/*.{yml,yaml}` files
3. Extracts action names and versions using regex
4. Compares against expected versions
5. If mismatches found:
   - Creates a new branch (`pinlock/update-actions-{timestamp}`)
   - Updates workflow files with correct versions
   - Commits and pushes changes
   - Creates a pull request with summary

## Output Example

```
🔒 Pinlock starting...
📋 Loaded 3 expected action versions
🔍 Found 2 workflow files

⚠️  Found version mismatches in 1 file(s):

  📄 .github/workflows/ci.yaml
    • actions/checkout: 11bd719... → 8e8c483...
    • actions/setup-python: abc1234... → 0b93645...

🌿 Creating branch: pinlock/update-actions-20251205-090333
📝 Updating workflow files...
  ✓ Updated .github/workflows/ci.yaml
💾 Committing changes...
⬆️  Pushing branch to origin...
🔀 Creating pull request...
✅ Pull request created successfully!
```

## Requirements

- Python 3.12+
- Git configured with user name/email
- GitHub CLI (`gh`) for PR creation
- `GITHUB_TOKEN` environment variable set (for PR creation)

## Local Testing

You can test Pinlock locally before using it in CI:

```bash
# Install Python 3.12+
python3 --version

# Run in dry-run mode (preview changes)
python3 pinlock.py --repo /path/to/repo --config /path/to/repo/dependactionbot.json --dry-run

# Run with actual changes
python3 pinlock.py --repo /path/to/repo --config /path/to/repo/dependactionbot.json
```

## Best Practices

1. **Review Generated PRs**: Always review the changes before merging
2. **Gradual Adoption**: Start with dry-run mode to understand the behavior
3. **Version Strategy**: Choose between:
   - Full commit SHAs (most secure, less readable)
   - Tags (readable, but subject to re-tagging)
4. **Update Frequency**: Schedule regular updates (weekly is recommended)
5. **Monitor PRs**: Keep an eye on failed PR creation (gh CLI issues)

## Troubleshooting

### PR creation fails
Ensure:
- `GITHUB_TOKEN` is available
- `gh` CLI is installed (usually pre-installed in GitHub Actions)
- Repository has write permissions configured

### No changes detected
- Verify `dependactionbot.json` exists and is valid JSON
- Check action names match exactly (case-sensitive)
- Ensure workflow files contain `uses:` statements

### Git errors
- Verify user.name and user.email are configured
- Check branch permissions
- Ensure no existing branch with the same name

## License

See LICENSE in the actions repository.
