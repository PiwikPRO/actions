import json

import pytest
from config import ConfigLoader
from copier import Copier
from detectors import CopyDetector, OperationDetectorChain
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
                        {
                            "project": "promil",
                            "source": "recursive/**/*.txt",
                            "destination": "somedir/recursive/",
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
            "/tmp/foo/other/level/due.txt": "blabla-overwritten",
            "/tmp/foo/recursive/due.txt": "blabla",
            "/tmp/foo/recursive/one/due.txt": "blabla",
            "/tmp/foo/recursive/one/two/due.txt": "blabla",
            "/tmp/foo/recursive/one/two/due.doc": "blabla",
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )


def test_copier(filesystem):
    copier = Copier(
        OperationDetectorChain(
            CopyDetector(
                "/tmp/foo",
                "/tmp/bar",
                "Νίκος Καζαντζάκης",
                "master",
                ConfigLoader.default("/tmp/foo", "/tmp/bar", filesystem).load(
                    "/tmp/techdocs/config.json"
                ),
            )
        ).operations(filesystem),
        filesystem,
    )

    copier.execute()

    assert filesystem.is_file("/tmp/bar/docs/promil/bla.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/one.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/two.md")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/inner/other-dir/foo.md")
    assert not filesystem.is_file("/tmp/bar/docs/promil/somedir/first.txt")
    assert not filesystem.is_file("/tmp/bar/docs/promil/somedir/second.txt")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/uno.txt")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/due.txt")
    assert not filesystem.is_file("/tmp/bar/docs/promil/somedir/non-text.md")
    assert not filesystem.is_file("/tmp/bar/docs/promil/somedir/level/due.txt")
    assert filesystem.read_string("/tmp/bar/docs/promil/somedir/due.txt") == "blabla"
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/recursive/due.txt")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/recursive/one/due.txt")
    assert filesystem.is_file("/tmp/bar/docs/promil/somedir/recursive/one/two/due.txt")
    assert not filesystem.is_file("/tmp/bar/docs/promil/somedir/recursive/one/two/due.doc")
