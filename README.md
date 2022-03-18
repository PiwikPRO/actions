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
        uses: PiwikPRO/actions/dtools@v1
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

      - name: Run linters
        uses: PiwikPRO/actions/go/lint@v1
...
```

### Test

Installs golang and runs tests

Example usage: 
```yaml
...
  steps:
      - name: Check out repository code
        uses: actions/checkout@v2

      - name: Run linters
        uses: PiwikPRO/actions/go/test@v1
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
        uses: PiwikPRO/actions/go/setup/integration@v1

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
        uses: PiwikPRO/actions/go/release@v1
        with:
          binary-name: barman
          main-file: main.go

...
```