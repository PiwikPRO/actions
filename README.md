# Actions

Custom github actions used both internally and externally by Piwik PRO employees. This repo is public and licensed on MIT license, but contains some actions, that cannot be launched without Piwik PRO proprietary components or secrets - sorry!

## Dependabot

[Dependabot](https://github.com/dependabot) is a tool to automated dependency updates built into GitHub.

### Update changelog

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
              uses: PiwikPRO/actions/dependabot/update_changelog@dependabot
```

Info: You should copy not only step, but also another parts above (run only on labeled pull requests with label `dependencies`) to work it correctly.

## Dtools

Dtools is internal Piwik PRO CLI used to abstract docker registry and artifacts manipulation. It is proprietary, requires secrets present only in Piwik PRO Github organization and thus is not usable outside of Piwik PRO. 

### Setup

Downloads and installs dtools binary on worker node.

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

      - name: Build the image
        run: docker build .
...
```

### Push

Pushes the image to docker registry (currently ACR only)

Example usage: 
```yaml
...
  steps:

      # Copy-pasting this snippet is enough, as secrets.DTOOLS_TOKEN is exposed on organization level in Piwik PRO
      - name: Push the image to registry
        uses: PiwikPRO/actions/dtools/push@master
        with:
          dtools-token: ${{ secrets.DTOOLS_TOKEN }}
          image: "framework/oma"
          destination-tag: my-custom-tag # optional, by default GitHub ref name

...
```

---

## Go

Contains common logic for continuous integration of Piwik PRO golang projects.

### Lint

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

### Test

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

### Integration tests setup (pytest)

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

### Attach binary as github release when tag is built

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

## Coverage (internal)

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


## Inclint (internal)

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