# Shared github actions

<!--toc:start-->
- [Actions](#actions)
  - [Dependabot](#dependabot)
    - [Update changelog](#update-changelog)
  - [Changelog](#changelog)
  - [Using aws-cli with proxy](#using-aws-cli-with-proxy)
  - [Dtools](#dtools)
  - [Godtools](#godtools)
    - [Login](#login)
    - [Push](#push)
    - [Setup](#setup)
  - [Go](#go)
    - [Lint](#lint)
    - [Push dir to s3](#push-dir-to-s3)
    - [Test](#test)
    - [Integration tests setup (pytest)](#integration-tests-setup-pytest)
    - [Attach binary as github release when tag is built](#attach-binary-as-github-release-when-tag-is-built)
  - [Python](#python)
    - [Lint](#lint)
  - [Coverage (internal)](#coverage-internal)
  - [Inclint (internal)](#inclint-internal)
  - [JavaScript](#javascript)
    - [LTS-lint](#lts-lint)
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
      - uses: actions/checkout@v3
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
        uses: actions/checkout@v2

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
        uses: actions/checkout@v2

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
        uses: actions/checkout@v2
      
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
        uses: actions/checkout@v2

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
        uses: actions/checkout@v2

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
        uses: actions/checkout@v2

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
First, make sure, that `black` and `flake8` are downloaded and available in your PATH.
Then clone this repository and set apropriate settings in preferences:

`ctrl+shift+p -> Preferences: Open settings (JSON)`

and set:
```
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": [
        "--config",
        "/home/kosto/Projects/promil/actions/python/lint/pyproject.toml"
    ],
    "editor.formatOnSave": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
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

#### LTS-lint

This action runs [prettier](https://prettier.io) and [eslint](https://eslint.org/)
on the target repository. It is currently used exclusively in the
[onprem platform](https://github.com/PiwikPRO/Promil-platform-onprem)
by the LTS team.
This action does not provide any configuration for the linters,
it relies on a configfile (such as `package.json`) located in the target repository,
making it as generic as possible.

```yaml
# Basic usage
      - uses: actions/checkout@v3
      - name: Run linters
        uses: PiwikPRO/actions/javascript/lts-lint@master

# If eslint and prettier are defined in the package.json
      - uses: actions/checkout@v3
      - name: Run linters
        uses: PiwikPRO/actions/javascript/lts-lint@master
        with:
          install-command: npm install
```

