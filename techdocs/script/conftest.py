import json

import pytest

from filesystem import MockFilesystem


@pytest.fixture
def filesystem():
    return MockFilesystem(
        {
            "/tmp/techdocs/config.json": json.dumps(
                {
                    "documents": [
                        {
                            "project": "promil",
                            "source": "README.md",
                            "destination": "bla.md",
                        },
                        {
                            "project": "promil",
                            "source": "docs/*",
                            "destination": "somedir/",
                            "exclude": [
                                "docs/internal/*",
                                "docs/*.txt",
                            ],
                        },
                        {
                            "project": "promil",
                            "source": "other/*.txt",
                            "destination": "somedir/",
                        },
                    ],
                }
            ),
            "/tmp/foo/README.md": "blabla",
            "/tmp/foo/docs/one.md": "blabla",
            "/tmp/foo/docs/first.txt": "blabla",
            "/tmp/foo/docs/second.txt": "blabla",
            "/tmp/foo/docs/inner/other-dir/foo.md": "blabla",
            "/tmp/foo/docs/two.md": "blabla",
            "/tmp/foo/docs/internal/int.md": "blabla",
            "/tmp/foo/other/uno.txt": "blabla",
            "/tmp/foo/other/due.txt": "blabla",
            "/tmp/foo/other/non-text.md": "blabla",
            "/tmp/foo/other/level/due.txt": "blabla",
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )

