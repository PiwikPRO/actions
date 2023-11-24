# Copy script

The script copies files and directories between source and destination paths, according to configuration passed in a JSON file. Usage:

```shell
python cli.py copy --from /tmp/foo --to /tmp/bar --config /tmp/techdocs/config.json 
```

## Config file

Example structure of a config file:

```json
{
    "project": "promil",
    "documents": [
        {"source": "README.md", "destination": "docs/promil/bla.md"},
        {"source": "docs/*", "destination": "docs/promil/somedir/", "exclude": ["docs/internal/*"]},
    ],
}
```

## Testing

```shell
pip install -r requirements.txt
python -m pytest
```

## Code style

You should adhere to the configs used by local python action, apply the formatting as follows:

```shell
black --config ../../python/lint/pyproject.toml .
isort --sp ../../python/lint/.isort.cfg .
```
