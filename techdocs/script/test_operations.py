import json
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from config import Config
from filesystem import MockFilesystem
from operations import (
    CopyDetector,
    DeleteDetector,
    FilesystemOperation,
    Index,
    IndexItem,
    IndexLoader,
)


@pytest.mark.parametrize(
    "file,rule_source,rule_destination,expected_source,expected_destination",
    (
        (  # if source is a file, destination a directory, copy the file directly into the directory
            "docs/promil/foo.md",
            "foo.md",
            "stacks/Promil-stack-analytics/",
            "/home/foobar/docs/promil/foo.md",
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/foo.md",
        ),
        (  # if source is a directory, destination a directory, copy the directory into the directory,
            # recursively, including the subdirectory structure
            "docs/promil/bla/huehue/foo.md",
            "docs/*",
            "stacks/Promil-stack-analytics/",
            "/home/foobar/docs/promil/bla/huehue/foo.md",
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/promil/bla/huehue/foo.md",
        ),
        (  # if source is a file, destination a file, copy the file directly into the file
            "docs/promil/foo.md",
            "docs/promil/foo.md",
            "stacks/Promil-stack-analytics/bar.md",
            "/home/foobar/docs/promil/foo.md",
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/bar.md",
        ),
    ),
)
def test_copy_create_operation(
    file, rule_source, rule_destination, expected_source, expected_destination
):
    detector = CopyDetector("/home/foobar", "/tmp/Tech-docs", Config([]))
    copy_operation = detector._create_operation(
        MockFilesystem(
            {"/tmp/Tech-docs/projects.json": json.dumps({"promil": {"path": "docs/promil"}})}
        ),
        file,
        Mock(
            config=Mock(
                project="promil",
                source=rule_source,
                destination=rule_destination,
            )
        ),
    )
    assert copy_operation.source_abs == expected_source
    assert copy_operation.destination_abs == expected_destination


def test_index_load():
    fs = MockFilesystem(
        {
            "/foo/index/Promil-platform-foo/42af564a885e1f38be3f411de2584efc3462bba68e9b5ea6dc39364b061d0a8f": json.dumps(
                {
                    "file": "heheszek",
                    "repo": "Promil-platform-foo",
                }
            )
        }
    )

    items = IndexLoader.load("/foo/index", fs).items

    assert items[0].file == "heheszek"
    assert items[0].repo == "Promil-platform-foo"
    assert len(items) == 1


def test_index_save():
    fs = MockFilesystem({})

    index = Index(
        (
            IndexItem("heheszek", "Promil-platform-foo"),
            IndexItem("foo/bar", "Promil-platform-foo"),
            IndexItem("baz/huehue", "Promil-platform-bar"),
        )
    )
    IndexLoader.save(index, "/foo/index", fs)

    assert list(sorted(fs.scan("/foo/index", ".*"))) == list(
        sorted(
            [
                "Promil-platform-foo/42af564a885e1f38be3f411de2584efc3462bba68e9b5ea6dc39364b061d0a8f",
                "Promil-platform-foo/cc5d46bdb4991c6eae3eb739c9c8a7a46fe9654fab79c47b4fe48383b5b25e1c",
                "Promil-platform-bar/4db8a688c5803846883870d0e15d84c33fb492ad5d8b67a9b7199d3eeeaa1907",
            ]
        )
    )

    assert json.loads(
        fs.read_string(
            "/foo/index/Promil-platform-foo/42af564a885e1f38be3f411de2584efc3462bba68e9b5ea6dc39364b061d0a8f"
        )
    ) == {
        "file": "heheszek",
        "repo": "Promil-platform-foo",
    }


def test_delete():
    fs = MockFilesystem(
        {
            "/tmp/Promil/a-file": "a-file-content",
            "/tmp/dst/a-file": "a-file-content",
            "/tmp/dst/a-file-that-does-not-exist-anymore": "blabla",
        }
    )
    mock_detector = Mock(
        detect=Mock(
            return_value=[
                FilesystemOperation(
                    source_abs="/tmp/Promil/a-file",
                    destination_abs="/tmp/dst/a-file",
                    type=FilesystemOperation.TYPE_COPY,
                )
            ]
        )
    )
    index = Index(
        (
            IndexItem("a-file", "Promil"),
            IndexItem("a-file-that-does-not-exist-anymore", "Promil"),
        )
    )
    detector = DeleteDetector(
        "Promil",
        index,
        "/tmp/Promil",
        "/tmp/dst",
        mock_detector,
    )

    operations = detector.detect(fs)

    assert operations[0].type == FilesystemOperation.TYPE_COPY
    assert operations[0].source_abs == "/tmp/Promil/a-file"
    assert operations[0].destination_abs == "/tmp/dst/a-file"
    assert operations[1].type == FilesystemOperation.TYPE_DELETE
    assert operations[1].source_abs == "/tmp/dst/a-file-that-does-not-exist-anymore"
    assert operations[1].destination_abs is None
    assert index.items == (IndexItem("a-file", "Promil"),)
    assert index.removed == (IndexItem("a-file-that-does-not-exist-anymore", "Promil"),)
