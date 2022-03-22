# Actions

Custom github actions used both internally and externally by Piwik PRO employees. This repo is public and licensed on MIT license, but contains some actions, that cannot be launched without Piwik PRO proprietary components or secrets - sorry!

## Actions

### Dtools

Dtools is internal Piwik PRO CLI used to abstract docker registry and artifacts manipulation. It is proprietary, requires secrets present only in Piwik PRO Github organization and thus is not usable outside of Piwik PRO. 

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2

      # Copy-pasting this snippet is enough, as all of those variables are exported on organization level in Piwik PRO
      - name: Download dtools
        uses: PiwikPRO/actions/dtools@3.0.0
        with:
          dtools-token: ${{ secrets.DTOOLS_TOKEN }}
          reporeader-private-key: ${{ secrets.REPOREADER_PRIVATE_KEY }}
          reporeader-application-id: ${{ secrets.REPOREADER_APPLICATION_ID }}

      - name: Push some image
        env:
          PP_DTOOLS_TOKEN: ${{ secrets.DTOOLS_TOKEN }}
        run: dtools dcr push ...
...
```
---------

## Go

Contains common logic for Piwik PRO golang projects.

### Lint

Installs golang and golangci-lint, runs linter tests.


Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2

      # simple linting, uses .golangci configiration file from the repo that is being linted:
      - name: Run linters
        uses: PiwikPRO/actions/go/lint@3.0.0

      # or more sophisticated linter, using common configuration for all repositories and enforcing incremental improvements with every PR:
      - name: Run linters
        uses: PiwikPRO/actions/go/lint@3.0.0
        with:
          inclint: "true"
          inclint-aws-access-key-id: ${{ secrets.COVERAGE_S3_ACCESS_KEY_ID }}
          inclint-aws-secret-access-key: ${{ secrets.COVERAGE_S3_SECRET_ACCESS_KEY }}
          inclint-reporeader-application-id: ${{ secrets.COVERAGE_APPLICATION_ID }}
          inclint-reporeader-private-key: ${{ secrets.COVERAGE_PRIVATE_KEY }}

...
```

**Configure VSCode to use common linter configuration**

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

### Test

Installs golang and runs tests

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2
      
      # simple tests without code coverage:
      - name: Run unit tests
        uses: PiwikPRO/actions/go/test@3.0.0

      # or, if you'd like your coverage to be measured with every PR:
      - name: Run unit tests
        uses: PiwikPRO/actions/go/test@1.0.0
        with:
          cov: "true"
          cov-aws-access-key-id: ${{ secrets.COVERAGE_S3_ACCESS_KEY_ID }}
          cov-aws-secret-access-key: ${{ secrets.COVERAGE_S3_SECRET_ACCESS_KEY }}
          cov-reporeader-application-id: ${{ secrets.COVERAGE_APPLICATION_ID }}
          cov-reporeader-private-key: ${{ secrets.COVERAGE_PRIVATE_KEY }}

...
```

### Integration tests setup

As most of our golang projects use pytest for integration tests, this action installs golang and pytest, but does not run the tests.

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2

      - name: Setup integration tests
        uses: PiwikPRO/actions/go/setup/integration@3.0.0

      - name: Run integration tests
        env:
          SOME_IMPORTANT_ENV_VAR: ${{ secrets.SOME_IMPORTANT_ENV_VAR }}
        run: py.test -v --tb=short

...
```

### Attach binary as github release when tag is built

Releases the binary when the tag is built. This action can also automatically update the version of your binary to match the tag, in future it will be better parametrized.

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2

      - name: Release the binary
        uses: PiwikPRO/actions/go/release@3.0.0
        with:
          binary-name: barman
          main-file: main.go

...
```

## Coverage (internal)

This action should not probably used by workflows, rather by other actions, that implement unit tests for given languages. The action allows storing coverge of given branch in AWS S3 and comparing coverage results during PRs. It ensures, that coverage is incrementally improved with time, by enforcing small improvement with every PR, up to given threshold (currently 80%).

Example usage
```yaml

    - name: Run coverage action
      uses: PiwikPRO/actions/coverage@3.0.0
      if: ${{ inputs.cov == 'true' }}
      with:
        aws-access-key-id: ${{ inputs.cov-aws-access-key-id }}
        aws-secret-access-key: ${{ inputs.cov-aws-secret-access-key }}
        head-coverage: ${{ steps.get-coverage.outputs.coverage }}
        github-token: ${{ steps.get-token.outputs.token }}
        threshold: ${{ inputs.cov-threshold }}

```


## Inclint (internal)

This action should not probably used by workflows, rather by other actions, that implement linter tests for given languages. The action allows storing amount of linter errors for given branch in AWS S3 and comparing amount of linter errors results during PRs. It ensures, that amount of linter errors is incrementally decreased with time, by enforcing small improvement with every PR.

Example usage
```yaml

    - name: Run inclint action
      uses: PiwikPRO/actions/inclint@3.0.0
      if: ${{ inputs.inclint == 'true' }}
      with:
        aws-access-key-id: ${{ inputs.inclint-aws-access-key-id }}
        aws-secret-access-key: ${{ inputs.inclint-aws-secret-access-key }}
        head-linter-errors: ${{ steps.get-linter-errors.outputs.lintererrors }}
        github-token: ${{ steps.get-token.outputs.token }}
        threshold: ${{ inputs.inclint-threshold }}

```