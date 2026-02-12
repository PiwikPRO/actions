# Shared github actions

<!--toc:start-->
- [Shared github actions](#shared-github-actions)
  - [Actions](#actions)
    - [Dependabot](#dependabot)
      - [Update changelog](#update-changelog)
    - [Developers Portal](#developers-portal)
    - [Changelog](#changelog)
    - [Using aws-cli with proxy](#using-aws-cli-with-proxy)
    - [Dtools](#dtools)
    - [Godtools](#godtools)
      - [Setup](#setup)
      - [Login](#login)
      - [Push](#push)
      - [Download artifacts](#download-artifacts)
    - [Go](#go)
      - [Lint](#lint)
      - [Push dir to s3](#push-dir-to-s3)
      - [Test](#test)
      - [Integration tests setup (pytest)](#integration-tests-setup-pytest)
      - [Attach binary as github release when tag is built](#attach-binary-as-github-release-when-tag-is-built)
    - [Python](#python)
      - [Lint](#lint-1)
      - [QA-Lint](#QA-lint)
    - [Coverage (internal)](#coverage-internal)
    - [Inclint (internal)](#inclint-internal)
    - [JavaScript](#javascript)
      - [Prettier](#prettier)
      - [ESLint](#eslint)
      - [Using Prettier and ESLint together](#using-prettier-and-eslint-together)
    - [K6](#k6)
    - [Benchmarking](#benchmarking)
    - [Platform outdated dependencies notifier](#platform-outdated-dependencies-notifier)
    - [Trigger version update](#trigger-version-update)
    - [1Password](#1Password)
      - [Get kubeconfig](#get-kubeconfig)
    - [Helm]
      - [Extract PiwikPRO CRDs](#extract-piwikpro-crds)
    - [Slack]
      - [Sending slack message to any channel](#slack)
    - [Allure](#allure)
      - [Generating allure report](#allure)
<!--toc:end-->

Custom github actions and reusable workflows used both internally and externally by Piwik PRO employees. This repo is public and licensed on MIT license, but contains some actions, that cannot be launched without Piwik PRO proprietary components or secrets - sorry!

## Actions

### Dependabot

[Dependabot](https://github.com/dependabot) is a tool to automated dependency updates built into GitHub.

#### Update changelog

It updates changelog for pull requests created by Dependabot

Example usage: 
```yaml
name: Update changelog when Dependabot creates pull request
on:
    pull_request_target:
        types: [ labeled ]

jobs:
    update_changelog:
        if: ${{ github.event.label.name == 'dependencies' }}
        runs-on: ubuntu-latest
        steps:
            - name: Update changelog
              uses: PiwikPRO/actions/dependabot/update_changelog@master
```

Info: You should copy not only step, but also another parts above (run only on labeled pull requests with label `dependencies`) to work it correctly.

### Developers Portal

This action adds a manually triggered workflow to publish part of OpenAPI stored in the repository. 

Add it as `publish_api_docs.yaml` to your repository `.github/workflows` directory:

```yaml
name: Publish public OpenAPI documentation

on:
  workflow_dispatch:
    inputs:
      repository_tag:
        description: 'Repository tag to process'
        required: true
        type: string

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  push-public-api-docs:
    uses: PiwikPRO/actions/.github/workflows/publish_api_docs.yaml@master
    secrets: inherit
    with:
      repository_tag: ${{ github.event.inputs.repository_tag }}
```

Then, you can trigger it manually from the Actions tab in your repository. As input you need to provide the tag 
of the repository you want to process.

For more details about its implementation head to [PiwikPRO/DevelopersPortal](https://github.com/PiwikPRO/DevelopersPortal#api-documentation)

### Changelog

Keep a changelog validator:
- `update` for checking if CHANGELOG.md has been updated on pull request. If commit message consists `skip-cl` verification is skipped
- `verify` check kacl structure using [python-kacl](https://github.com/mschmieder/python-kacl)

Example usage:
```
name: Check changelog update
on: pull_request
jobs:
  check_changelog_update:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - uses: actions/checkout@v4 # pin latest commit-hash
        with:
          ref: ${{ github.event.pull_request.head.ref }}
      - name: Verify CHANGELOG.md kacl-cl structure
        uses: PiwikPRO/actions/changelog/verify@master
      - name: Check if CHANGELOG.md is updated
        uses: PiwikPRO/actions/changelog/update@master
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Using aws-cli with proxy

It is possible to configure the step that using aws-cli binary to make the connection through proxy. To do this, you must set the appropriate [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-proxy.html).


Ready URIs are available under organization level secrets:

```
FORWARD_PROXY_HTTP
FORWARD_PROXY_HTTPS
```

Example usage:
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      # Copy-pasting this snippet is enough, as all of those variables are exposed on organization level in Piwik PRO
      - name: Download dtools
        uses: PiwikPRO/actions/dtools/setup@master
        with:
          dtools-token: ${{ secrets.DTOOLS_TOKEN }}
          reporeader-private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
          reporeader-application-id: ${{ secrets.REPOREADER_APPLICATION_ID }}
          include-registry: acr # acr is default value, could be a list (ecr, acr, docker_hub, internal_acr)

      - name: Download events
        uses: PiwikPRO/actions/dtools/s3_download
        env:
          HTTP_PROXY: ${{ secrets.FORWARD_PROXY_HTTP }}
          HTTPS_PROXY: ${{ secrets.FORWARD_PROXY_HTTPS }}
        with:
          dtools-token: ${{ secrets.DTOOLS_TOKEN }}
...
```

### Dtools

Dtools are deprecated now, please use [godtools](#godtools) instead.

### Godtools

[Godtools](https://github.com/PiwikPRO/godtools) is a tool for performing operations that require sharing sensitive credentials such as pulling docker images or s3 artifacts.

#### Setup

Downloads latest version of the `godtools` binary and makes it available in `PATH`.

Example usage:

```yaml
---
steps:
  - name: Download and setup godtools
    uses: PiwikPRO/actions/godtools/setup@master
    with:
      godtools-config: ${{ secrets.GODTOOLS_CONFIG }}
      godtools-key: ${{ secrets.GODTOOLS_KEY }}
      reporeader-private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
      reporeader-application-id: ${{ secrets.REPOREADER_APPLICATION_ID }}
```

#### Login

Allows to authenticate to docker registries. It requires [setup](#setup) action.

Example usage:

```yaml
---
steps:
  - name: Login to docker registries with godtools
    uses: PiwikPRO/actions/godtools/login@master
    with:
      godtools-config: ${{ secrets.GODTOOLS_CONFIG }}
      godtools-key: ${{ secrets.GODTOOLS_KEY }}
      registries: acr, docker-hub
```

#### Push

Allows to push docker images to authenticated registries. It requires both [setup](#setup) and [login](#login) actions.

Example usage:

```yaml
---
steps:
  - name: Push container image
    uses: PiwikPRO/actions/godtools/push@master
    with:
      image: repository/image
      godtools-config: ${{ secrets.GODTOOLS_CONFIG }}
      godtools-key: ${{ secrets.GODTOOLS_KEY }}
```

Check [optional inputs](https://github.com/PiwikPRO/actions/blob/master/godtools/push/action.yaml#L13) 
for additional configuration capabilities.

#### Download artifacts

Allows to download artifacts, like EventKeeper's `events`. It requires [setup](#setup) action.

Example usage:

```yaml
---
steps:
  - name: Download events
    uses: PiwikPRO/actions/godtools/download@master
    env:
      HTTP_PROXY: ${{ secrets.FORWARD_PROXY_HTTP }}
      HTTPS_PROXY: ${{ secrets.FORWARD_PROXY_HTTPS }}
    with:
      godtools-config: ${{ secrets.GODTOOLS_CONFIG }}
      godtools-key: ${{ secrets.GODTOOLS_KEY }}
      artifacts: events
      ref: master
```

---

### Go

Contains common logic for continuous integration of Piwik PRO golang projects.

#### Lint

Installs golang and golangci-lint, runs linter tests.


Example usage:
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      # Simple linting, uses .golangci configiration file from the repo that is being linted:
      - name: Run linters
        uses: PiwikPRO/actions/go/lint@master

      # More sophisticated linter, using common configuration for all repositories and enforcing incremental improvements with every PR.
      # Copy-pasting this snippet is enough, as all of those variables are exposed on organization level in Piwik PRO.
      - name: Run linters
        uses: PiwikPRO/actions/go/lint@master
        with:
          inclint: "true"
          inclint-aws-access-key-id: ${{ secrets.COVERAGE_S3_ACCESS_KEY_ID }}
          inclint-aws-secret-access-key: ${{ secrets.COVERAGE_S3_SECRET_ACCESS_KEY }}
          inclint-reporeader-application-id: ${{ secrets.COVERAGE_APPLICATION_ID }}
          inclint-reporeader-private-key: ${{ secrets.COVERAGE_PRIVATE_KEY }}

...
```

**Configure VSCode to use common linter configuration**

You can configure your local golangci-lint to use common configuration placed in this repository.
First, make sure, that golangci-lint is downloaded and available in your PATH.
Then clone this repository and set apropriate settings in preferences:

`ctrl+shift+p -> Preferences: Open settings (JSON)`

and set:
```
{
    "go.lintTool":"golangci-lint",
    "go.lintFlags": [
        "-c", "/home/kkaragiorgis/Projects/promil/actions/go/lint/.golangci.yml"
    ]
}
```
Replace `/home/kkaragiorgis/Projects/promil` to wherever you cloned `actions` repository.


**Preferred triggers for workflows using this action**
```yaml
on:
  pull_request:
  push:
    branches: ["master"]
```

#### Push dir to s3

Pushes provided dir to s3.

Example usage:
```yaml
...
  steps:
      - name: Producing some artifacts
        shell: bash
        run: make

      - name: Upload artifacts
        uses: PiwikPRO/actions/s3/upload@master
        with:
          aws-access-key-id: ${{ secrets.S3_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.S3_SECRET_ACCESS_KEY }}
          aws-bucket: my-sweet-artifacts-bucket
          aws-region: eu-central-1
          aws-http-proxy: ${{ secrets.FORWARD_PROXY_HTTP }}
          aws-https-proxy: ${{ secrets.FORWARD_PROXY_HTTPS }}          
          src-path: artifacts/
          dst-path: ${{ github.repository }}/@${{ github.ref_name }}/artifacts/
          echo-destination-index-html: true
...
```

#### Test

Installs golang and runs tests

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash
       
      # Simple tests without code coverage:
      - name: Run unit tests
        uses: PiwikPRO/actions/go/test@master

      # More sophisticated tests, calculates coverage and enforces small incremental improvements with every PR.
      # Uses AWS S3 to store per-repository and per-branch information about the coverage.
      - name: Run unit tests
        uses: PiwikPRO/actions/go/test@master
        with:
          cov: "true"
          cov-aws-access-key-id: ${{ secrets.COVERAGE_S3_ACCESS_KEY_ID }}
          cov-aws-secret-access-key: ${{ secrets.COVERAGE_S3_SECRET_ACCESS_KEY }}
          cov-reporeader-application-id: ${{ secrets.COVERAGE_APPLICATION_ID }}
          cov-reporeader-private-key: ${{ secrets.COVERAGE_PRIVATE_KEY }}
          # Optional - boundary value up to which the coverage should be increased
          cov-threshold: 80

...
```

**Preferred triggers for workflows using this action**
```yaml
on:
  pull_request:
  push:
    branches: ["master"]
```

#### Integration tests setup (pytest)

As most of our golang projects use pytest for integration tests, this action installs golang and pytest, but does not run the tests. The tests are not launched automatically by this action, because most of the integration tests suited require additional configuration in the form of env vars, and unfortunately Github Actions does not allow dynamic injection of configuration (eg. env vars) into already configured step.

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      - name: Setup integration tests
        uses: PiwikPRO/actions/go/setup/integration@master

      - name: Run integration tests
        env:
          SOME_IMPORTANT_ENV_VAR: ${{ secrets.SOME_IMPORTANT_ENV_VAR }}
        run: py.test -v --tb=short

...
```

#### Attach binary as github release when tag is built

Runs go build and releases the binary when the tag is built.

This action can also automatically update the version of your binary to match the tag, it assumes a certain convention:
1. It checks if there is `cmd/version.go` file present
2. If so, it replaces its contents with `package cmd \n const projectVersion = <current tag>`
3. After that it builds the binary. It does not commit or retag anything to git, only the local code is modified before the binary is build.

If `cmd/version.go` file does not exists, the version is not updated.


Example usage:
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      - name: Release the binary
        uses: PiwikPRO/actions/go/release@master
        with:
          binary-name: barman
          main-file: main.go

...
```


### Python

#### Lint

Run various python linters:
  * Flake8 - Check against pep8 violation (https://flake8.pycqa.org/en/latest/).
  * Black - Enforce `Black` code style (https://black.readthedocs.io/en/stable/).
  * Isort - Sort and format imports (https://pycqa.github.io/isort/).


Example usage:
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      # Simple linting, uses predefined configuration file from this repository:
      - name: Run linters
        uses: PiwikPRO/actions/python/lint@master
        with:
          use-black: true
          use-flake: true
          use-isort: true

...
```

**Configure VSCode to use common linter configuration**

You can configure your local environment to use common configuration placed in this repository.
First, make sure, that `black formatter` and `flake8` extenstions are downloaded and available.
Then clone this repository and set apropriate settings in preferences:

`ctrl+shift+p -> Preferences: Open settings (JSON)`

and set:
```
{
    "black-formatter.args": [
        "--config",
        "/home/kosto/Projects/promil/actions/python/lint/pyproject.toml"
    ],
    "editor.formatOnSave": true,
    "flake8.args": [
        "--config",
        "/home/kosto/Projects/promil/actions/python/lint/flake8.ini"
    ],
    "isort.args": [
        "--profile",
        "black",
        "--sp",
        "/home/kosto/Projects/promil/actions/python/lint/.isort.cfg"
    ],
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```
Replace `/home/kkaragiorgis/Projects/promil` to wherever you cloned `actions` repository.

#### QA-Lint

Example usage:
```yaml
...
    steps:
      - uses: actions/checkout@v4 # pin latest commit-hash
        with:
          ref: ${{ github.event.pull_request.head.ref }}

      - name: Run Linter
        uses: PiwikPRO/actions/python/qa-lint@master
...
```


### Coverage (internal)

This action should not probably used directly by workflows, rather by other actions, that implement unit tests for given languages. The action allows storing coverge of given branch in AWS S3 and comparing coverage results during PRs. It ensures, that coverage is incrementally improved with time, by enforcing small improvement with every PR, up to given threshold (currently 80%).

Example usage (in other action)
```yaml

    - name: Run coverage action
      uses: PiwikPRO/actions/coverage@master
      if: ${{ inputs.cov == 'true' }}
      with:
        aws-access-key-id: ${{ inputs.cov-aws-access-key-id }}
        aws-secret-access-key: ${{ inputs.cov-aws-secret-access-key }}
        head-coverage: ${{ steps.get-coverage.outputs.coverage }}
        github-token: ${{ steps.get-token.outputs.token }}
        threshold: ${{ inputs.cov-threshold }}

```


### Inclint (internal)

This action should not probably used directly by workflows, rather by other actions, that implement linter tests for given languages. The action allows storing number of linter errors for given branch in AWS S3 and comparing number of linter errors results during PRs. It ensures, that number of linter errors is incrementally decreased over time, by enforcing small improvement with every PR.

Example usage
```yaml

    - name: Run inclint action
      uses: PiwikPRO/actions/inclint@master
      if: ${{ inputs.inclint == 'true' }}
      with:
        aws-access-key-id: ${{ inputs.inclint-aws-access-key-id }}
        aws-secret-access-key: ${{ inputs.inclint-aws-secret-access-key }}
        head-linter-errors: ${{ steps.get-linter-errors.outputs.lintererrors }}
        github-token: ${{ steps.get-token.outputs.token }}
        threshold: ${{ inputs.inclint-threshold }}

```

### JavaScript

#### Prettier

This action runs [Prettier](https://prettier.io) to check formatting of JavaScript, JSON, YAML and Markdown files.
It relies on a configuration file (such as `.prettierrc` or `package.json`) located in the target repository.

```yaml
# Basic usage
      - uses: actions/checkout@v4
      - name: Run Prettier
        uses: PiwikPRO/actions/javascript/prettier@master

# If prettier is defined in the package.json
      - uses: actions/checkout@v4
      - name: Run Prettier
        uses: PiwikPRO/actions/javascript/prettier@master
        with:
          install-command: npm install
```

#### ESLint

This action runs [ESLint](https://eslint.org/) to verify JavaScript code quality.
It relies on a configuration file (such as `eslint.config.js` or `package.json`) located in the target repository.

```yaml
# Basic usage
      - uses: actions/checkout@v4
      - name: Run ESLint
        uses: PiwikPRO/actions/javascript/eslint@master

# If eslint is defined in the package.json
      - uses: actions/checkout@v4
      - name: Run ESLint
        uses: PiwikPRO/actions/javascript/eslint@master
        with:
          install-command: npm install
```

#### Using Prettier and ESLint together

When using both actions, install dependencies once and use `skip-install: true` to avoid duplicate installation:

```yaml
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm install
      - name: Run Prettier
        uses: PiwikPRO/actions/javascript/prettier@master
        with:
          skip-install: true
      - name: Run ESLint
        uses: PiwikPRO/actions/javascript/eslint@master
        with:
          skip-install: true
```

### K6

K6 action is a part of benchmarking workflow described below and on its own is not very useful. Here is the reference of parameters that can be passed to the action:

```yaml
name: Run k6
uses: PiwikPRO/actions/k6@master
with:
  script: dev/k6.js
  vus: 25
  duration: 60s
```

* `script` - path to the k6 script, relative to the repository root
* `vus` - number of virtual users, a k6 concept
* `duration` - duration of the test

### Benchmarking

This repository allows using continuous benchmarking approach, which you can easily plug into your CI system using few lines of YAML. The benchmarking pipeline works as follows:

* It runs a benchmarking script on every released tag and archives the results in artifactory.
* It runs the same benchmarking script during the pull request, if it detects a `/benchmark` comment. 
  * It compares the results with the average result of the last 5 tag benchmarks (if available).

**Important. The `/benchmark` comment won't work unless the workflow is already on main repo branch**, this is a limitation of GitHub Actions. Alternative approach, for tests would be to change the conditions, so that the rebuild is triggered on every commit to a PR. Try this approach when integrating this workflow into your repository, specific instructions are on the bottom.

In order to be able to run the pipeline, you need a `k6` benchmarking script. Here's how the action is invoked (internal example from one of our repositories):

```yaml .github/workflows/benchmark.yml
name: Benchmark
on:
  push:
    tags:
      - '*'
  issue_comment:
    types: [created]
jobs:
  k6:
    if: ${{ github.ref_type == 'tag' || (github.event.issue.pull_request && github.event.comment.body == '/benchmark') }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:

    - name: Generate PiwikPRO access token
      uses: PiwikPRO/github-app-token-generator@v1
      id: get-token
      with:
        private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
        app-id: ${{ secrets.REPOREADER_APPLICATION_ID }}

    - uses: actions/checkout@v4 # pin latest commit-hash
      with:
        submodules: true
        token: ${{ steps.get-token.outputs.token }}

    - name: Start the devenv
      run: ./dev/start.sh # 1 this need to be customized

    - name: Run k6
      uses: PiwikPRO/actions/benchmark/k6@master
      with:
        script: dev/k6.js # 2 this need to be customized
        vus: 25
        duration: 60s

    - name: Archive benchmark results
      uses: actions/upload-artifact@v4 # pin latest commit-hash
      with:
        name: summary
        path: summary.json

  publish:
    needs: k6
    uses: PiwikPRO/actions/.github/workflows/benchmarks_upload.yaml@master
    secrets: inherit
    with:
      artifact: summary
```

In order to add benchmarking capabilities to your CI, copy the above YAMl snippet, you also need to customize the following parts:

1. "Start the devenv" step. After the step, you should have a running web server or whatever you'd like to test, so that the `k6` script can hit it. It may be something like `docker-compose up -d`, or equivalent, depending on what you're using and how your development environment looks like.

2. The location and other parameters of the k6 script. It should be a path relative to the repository root. If you need that, you can set `env` key here and read the vars from the `k6` script.

To change the trigger from `/benchmark` comment to every PR commit, you can:

* Comment ` tags: - '*'` from the `on` section.
* Comment the `if` condition (`if: ${{ github.ref_type == 'tag' || (gi....`) from the `k6` job.

### Platform Outdated Dependencies Notifier
The Platform Outdated Dependencies Notifier action is a GitHub Action that notifies you when there are outdated dependencies in your project.
Is compares helm chart versions in the repository where action is executed with the latest versions of those charts in our helm charts source repository.
If case of any difference in versions, comment to PR with current/desired version is added. 

#### Usage
```yaml .github/workflows/validate_helm_charts_versions.yaml
name: Check Outdated Helm Charts
on:
  pull_request:
    branches:
      - develop
jobs:
  check-versions:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:

    - name: Generate PiwikPRO access token to charts repo
      uses: PiwikPRO/github-app-token-generator@v1
      id: get-token
      with:
        private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
        app-id: ${{ secrets.REPOREADER_APPLICATION_ID }}
        repository: PiwikPRO/Promil-helm-chart-repository-source

    - name: Compare chart versions
      uses: PiwikPRO/actions/platform-outdated-dependencies-notifier@master
      with:
        github-token-charts: ${{ steps.get-token.outputs.token }}
        github-token-platform: ${{ secrets.GITHUB_TOKEN }}
```

### Trigger version update

This action triggers a version update workflow in a target repository based on development branch commits or tags.
Main idea is to automate bumping explicit tmp images in stack repo to allow testing latest develop changes, without relying on unversioned tmp-develop branches.

**How It Works:**

For **dev branch commits**: When a commit is pushed to the dev branch, it generates a version string like `tmp-cf3ebd52` and triggers the `update-service-version.yaml` workflow in the target repository.

For **tags**: When a tag is created, it extracts the tag name (e.g., `1.32.4`) and checks if the tagged commit exists in the dev branch using `git merge-base --is-ancestor`. If the commit exists in dev, it triggers the workflow with the tag name as version. If not, it skips triggering (assumes hotfix from master).

#### Usage

```yaml .github/workflows/version_update.yaml
name: Trigger version update

on:
  workflow_run:
    # Name of the workflow that has to finish to trigger the version update  
    workflows: ["Build and Test"]
    types:
      - completed
    branches:
      - develop

# explicitly limit action permissions 
permissions:
  contents: read

jobs:
  trigger-update:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - name: Trigger version update
        uses: PiwikPRO/actions/version-update/trigger@master
        with:
          service-name: reporting
          target-repo: Promil-stack-analytics
          # Requires fine-grained PAT with "Actions: Read and write" permission as WORKFLOW_TRIGGER_TOKEN
          workflow-token: ${{ secrets.WORKFLOW_TRIGGER_TOKEN }}
```

#### Inputs

| Input | Description | Required | Default   |
|-------|-------------|----------|-----------|
| `service-name` | Name of the service to update (e.g., etl, reporting, ui) | Yes | -         |
| `target-repo` | Target repository to trigger workflow in | Yes | -         |
| `workflow-token` | GitHub token with workflow dispatch permissions (fine-grained PAT with "Actions: Read and write") | Yes | -         |
| `dev-branch` | Name of the development branch to validate tags against | No | `develop` |
| `target-workflow-ref` | Git ref to use when triggering the target workflow | No | `develop` |

#### Requirements

In the source repository (where this action runs):
- A fine-grained GitHub PAT with "Actions: Read and write" permission (in usage example stored as `WORKFLOW_TRIGGER_TOKEN` secret)
- The PAT must have access to the target repository

In the target repository:
- Must have an `update-service-version.yaml` workflow that accepts `service_name` and `version` inputs

### 1Password
#### Get kubeconfig
`1password/get-kubeconfig` action is a Github Action that fetches `kubeconfig` field from 1Password item and base64 decodes it.

Example usage:
```yaml
on:
  pull_request:
  push:
    branches: ["master"]
name: Test actions
jobs:
  test-get-kubeconfig:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    strategy:
      fail-fast: false
      max-parallel: 2
      matrix:
        infra-name:
          example-infra-1
          example-infra-2
    steps:
    - name: Check out repository code
      uses: actions/checkout@v4 # pin latest commit-hash

    - name: Get kubeconfig
      id: get-kubeconfig
      uses: PiwikPRO/actions/1password/get-kubeconfig@master
      with:
        op-sa-token: ${{ secrets.OP_PREPROD_KUBECONFIG_SA_TOKEN}}
        op-vault: ${{ secrets.OP_PREPROD_KUBECONFIG_VAULT }}
        op-item: ${{ matrix.infra-name }}

    - name: Echo get-kubeconfig
      shell: bash
      run: echo ${{ steps.get-kubeconfig.outputs.kubeconfig }}
```

### Helm
#### Extract PiwikPRO CRDs
`helm/extract-piwikpro-crds` actions is a Github Action that extracts CRD definitions and prepares artifact with them. 
It is used in order to upload CRDs onto `techdocs`.

Example usage:
```yaml
name: Documentation
on: [ push, pull_request ]
jobs:
  prepare-crds:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Check out repository code
        uses: actions/checkout@v4 # pin latest commit-hash

      - name: Prepare CRDs
        uses: PiwikPRO/actions/helm/extract-piwikpro-crds@DEVOPS-7919
        with:
          private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
          app-id: ${{ secrets.REPOREADER_APPLICATION_ID }}
          artifact-name: crds

  push:
    needs: prepare-crds
    uses: PiwikPRO/actions/.github/workflows/push_docs.yaml@master
    secrets: inherit
    with:
      artifact: crds
      config: |
        {
          "documents": [
            {
              "source": ".techdocs-artifact/*",
              "destination": "development/apis/kubernetes/",
              "project": "promil"
            }
          ]
        }
```

### Slack

You can send a slack message from any pipeline, for that:
* Go to your channel, ping `@Github actions` bot and invite it to the channel
* Add the following step to your workflow; the secret is inherited from global, per-organization secrets, so just copy/paste the below, change channel and message, period.
* All the possibilities are listed here: https://tools.slack.dev/slack-github-action/sending-techniques/sending-data-slack-api-method/

```

    - name: Post text to a Slack channel
      uses: slackapi/slack-github-action@b0fa283ad8fea605de13dc3f449259339835fc52 # v2.1.0
      with:
        method: chat.postMessage
        token: ${{ secrets.SLACK_BOT_TOKEN }}
        payload: |
          channel: data-warehouse-alerts
          text: "howdy! This is a test message from the data warehouse pipeline."
```

### Allure

Paste the following code into your workflows under the `.github` directory.

Before the run tests step:
``` 
      - name: Generate S3 paths
        uses: PiwikPRO/actions/allure/s3_path@master
        with:
          environment: ${{ inputs.environment }} # usually it’s just inputs.environment or matrix.environment
          team: 'qa-team'  # required field. cia/mit etc.
          matrix_block: ${{ matrix.testblock }} # optional field. Use if the matrix strategy is used.
          retention: '30days'  # optional field. Default value is 30days
```

After the run tests step:
```
      - name: Report generating
        uses: PiwikPRO/actions/allure/history@master
        with:
          aws-access-key-id: ${{ secrets.ARTIFACTORY_S3_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.ARTIFACTORY_S3_SECRET_ACCESS_KEY }}
          aws-http-proxy: ${{ secrets.FORWARD_PROXY_HTTP }}
          aws-https-proxy: ${{ secrets.FORWARD_PROXY_HTTPS }}
          environment:  # usually it’s just inputs.environment or matrix.environment
          team: 'qa-team' # required field. cia/mit etc.
          enable-history: 'true'  # optional field. Default value is false. 
          retention: '60days' # optional field. Default value is 30days
```

Above setup will allow you to preserve the history of test runs in your Allure Report.