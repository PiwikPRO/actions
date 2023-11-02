# Copy script

The script copies files and directories between source and destination paths, accodrding to configuration passed in a JSON file. Usage:

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
        {"source": "docs/*", "destination": "docs/promil/somedir", "exclude": ["docs/internal/*"]},
    ],
}
```

## Testing

```shell
pip install -r requirements.txt
python -m pytest
```
