import json

import pytest

from config import ConfigError, ConfigLoader
from filesystem import MockFilesystem


@pytest.mark.parametrize(
    "config,is_valid",
    (
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "README.md",
                        "destination": "docs/promil/bla.md",
                    },
                    {
                        "project": "promil",
                        "source": "docs/*",
                        "destination": "docs/promil/somedir/",
                        "exclude": ["docs/internal/*"],
                    },
                ],
            },
            True,
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "README.md",
                        "destination": "docs/promil/bla.md",
                    },
                    {
                        "project": "promil",
                        "source": "docs/*",
                        "destination": "/docs/promil/somedir/",
                        "exclude": ["docs/internal/*"],
                    },
                ],
            },
            False,  # Absolute destination path
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "*.md",
                        "destination": "docs/promil/",
                    }
                ],
            },
            True,  # Wildcard for file extension
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "*.md",
                        "destination": "docs/promil/test.md",
                    }
                ],
            },
            False,  # Wildcard for file extension pointing single file
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "README.md",
                        "destination": "bla.md",
                    },
                    {
                        "project": "promil",
                        "source": "docs/blabla",
                        "destination": "somedir/",
                        "exclude": ["docs/internal/*"],
                    },
                ],
            },
            False,  # Source file does not exist
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "README.md",
                        "destination": "bla.md",
                    },
                    {
                        "project": "foo",
                        "source": "docs/*",
                        "destination": "somedir/",
                        "exclude": ["docs/internal/*"],
                    },
                ],
            },
            False,  # Project does not exist
        ),
        (
            {
                "documents": [
                    {
                        "project": "promil",
                        "source": "README.md",
                        "destination": "bla.md",
                    },
                    {
                        "project": "promil",
                        "source": "docs/**/somepath/*",
                        "destination": "somedir/file.md",
                        "exclude": ["docs/internal/*"],
                    },
                ],
            },
            False,  # Wildcard in the middle of the source path and destination is a file
        ),
    ),
)
def test_config_violations(config, is_valid):
    fs = MockFilesystem(
        {
            "/tmp/techdocs/config.json": json.dumps(config),
            "/tmp/foo/README.md": "blabla",
            "/tmp/foo/docs/inner/other-dir/foo.md": "blabla",
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )
    if is_valid:
        ConfigLoader.default("/tmp/foo", "/tmp/bar", fs).load("/tmp/techdocs/config.json")
    else:
        with pytest.raises(ConfigError):
            ConfigLoader.default("/tmp/foo", "/tmp/bar", fs).load("/tmp/techdocs/config.json")


def test_skip_invalid_documents():
    fs = MockFilesystem(
        {
            "/tmp/techdocs/config.json": json.dumps(
                {
                    "documents": [
                        {
                            "project": "not-existing-project",
                            "source": "README.md",
                            "destination": "docs/promil/bla.md",
                        },
                        {
                            "project": "promil",
                            "source": "docs/*",
                            "destination": "docs/promil/somedir/",
                            "exclude": ["docs/internal/*"],
                        },
                    ],
                }
            ),
            "/tmp/foo/README.md": "blabla",
            "/tmp/foo/docs/inner/other-dir/foo.md": "blabla",
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )

    config = ConfigLoader.default("/tmp/foo", "/tmp/bar", fs).load(
        "/tmp/techdocs/config.json", skip_invalid_documents=True
    )
    assert len(config.documents) == 1
