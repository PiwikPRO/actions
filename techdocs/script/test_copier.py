import json

import pytest
from config import ConfigLoader
from copier import Copier
from filesystem import MockFilesystem
from operations import CopyDetector


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
                            "exclude": ["docs/internal/*"],
                        },
                    ],
                }
            ),
            "/tmp/foo/README.md": "blabla",
            "/tmp/foo/docs/one.md": "blabla",
            "/tmp/foo/docs/inner/other-dir/foo.md": "blabla",
            "/tmp/foo/docs/two.md": "blabla",
            "/tmp/foo/docs/internal/int.md": "blabla",
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )


def test_copier(filesystem):
    copier = Copier(
        CopyDetector(
            "/tmp/foo",
            "/tmp/bar",
            ConfigLoader.default("/tmp/foo", "/tmp/bar", filesystem).load(
                "/tmp/techdocs/config.json"
            ),
        ),
        filesystem,
    )

    copier.execute("/tmp/foo")

    assert filesystem.is_file("/tmp/bar/docs/promil/bla.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/one.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/two.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/inner/other-dir/foo.md")
    # assert 1 == 2
