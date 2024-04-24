import json
from unittest.mock import Mock

import pytest
from config import Config, ConfigDocumentEntry
from detectors import (
    CopyDetector,
    DeleteDetector,
    PlantUMLDiagramsDetector,
    UnnecessaryOperationsFilteringDetector,
    swap_extension,
)
from filesystem import MockFilesystem
from index import FileIndex, FileIndexItem, FileIndexLoader
from operations import GenericFileCopyOperation, DeleteOperation
from detectors import OpenAPIDetector


def test_copy():
    fs = MockFilesystem(
        {
            "/tmp/Promil/docs/README.md": "readme",
            "/tmp/Promil/docs/inner/setup.md": "setup",
            "/tmp/Promil/docs/inner/maintenance.md": "maintenance",
            "/tmp/dst/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
        }
    )

    detector = CopyDetector(
        "/tmp/Promil",
        "/tmp/dst",
        "Γιώργος Σεφέρης",
        "master",
        Config([ConfigDocumentEntry("promil", "docs/*", ".", [])]),
    )

    operations = detector.detect(fs, [])

    assert len(operations) == 3
    assert operations[0].name() == "copy"
    assert operations[0].source_abs == "/tmp/Promil/docs/README.md"
    assert operations[0].destination_abs == "/tmp/dst/docs/promil/README.md"
    assert operations[1].name() == "copy"
    assert operations[1].source_abs == "/tmp/Promil/docs/inner/setup.md"
    assert operations[1].destination_abs == "/tmp/dst/docs/promil/inner/setup.md"
    assert operations[2].name() == "copy"
    assert operations[2].source_abs == "/tmp/Promil/docs/inner/maintenance.md"
    assert operations[2].destination_abs == "/tmp/dst/docs/promil/inner/maintenance.md"


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
def test_copy_create_operation_variants(
        file, rule_source, rule_destination, expected_source, expected_destination
):
    detector = CopyDetector(
        "/home/foobar", "/tmp/Tech-docs", "Οδυσσέας Ελύτης", "master", Config([])
    )
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
            "/foo/index/Promil-platform-foo/42af564a885e1f38be3f411de2584efc3462bba68e9b5ea6dc39364b061d0a8f":
                json.dumps(
                {
                    "file": "heheszek",
                    "repo": "Promil-platform-foo",
                }
            )
        }
    )

    items = FileIndexLoader.load("/foo/index", fs).items

    assert items[0].file == "heheszek"
    assert items[0].repo == "Promil-platform-foo"
    assert len(items) == 1


def test_index_save():
    fs = MockFilesystem({})

    index = FileIndex(
        (
            FileIndexItem("heheszek", "Promil-platform-foo"),
            FileIndexItem("foo/bar", "Promil-platform-foo"),
            FileIndexItem("baz/huehue", "Promil-platform-bar"),
        )
    )
    FileIndexLoader.save(index, "/foo/index", fs)

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
    index = FileIndex(
        (
            FileIndexItem("a-file", "Promil"),
            FileIndexItem("a-file-that-does-not-exist-anymore", "Promil"),
        )
    )
    detector = DeleteDetector(
        "Promil",
        index,
        "/tmp/Promil",
        "/tmp/dst",
    )

    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/a-file",
                destination_abs="/tmp/dst/a-file",
            )
        ],
    )

    assert operations[0].name() == "copy"
    assert operations[0].source_abs == "/tmp/Promil/a-file"
    assert operations[0].destination_abs == "/tmp/dst/a-file"
    assert operations[1].name() == "delete"

    assert operations[1].destination_abs == "/tmp/dst/a-file-that-does-not-exist-anymore"
    assert index.items == (FileIndexItem("a-file", "Promil"),)
    assert index.removed == (FileIndexItem("a-file-that-does-not-exist-anymore", "Promil"),)


def test_filtering():
    fs = MockFilesystem(
        {
            "/tmp/Promil/a-file": "a-file-content",
            "/tmp/dst/a-file": "a-file-content",
            "/tmp/dst/a-file-that-does-not-exist-anymore": "blabla",
        }
    )
    detector = UnnecessaryOperationsFilteringDetector()

    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/a-file",
                destination_abs="/tmp/dst/a-file",
            ),
            DeleteOperation(
                destination_abs="/tmp/dst/a-file-that-does-not-exist-anymore",
            ),
        ],
    )

    assert len(operations) == 1
    assert operations[0].name() == "delete"
    assert operations[0].destination_abs == "/tmp/dst/a-file-that-does-not-exist-anymore"


def test_plantuml():
    # given
    fs = MockFilesystem(
        {
            "/tmp/Promil/a-file.puml": "a-file-content",
            "/tmp/Promil/b-file": "b-file-content",
        }
    )
    detector = PlantUMLDiagramsDetector(
        generator=Mock(
            generate=Mock(
                return_value="<xml><svg foo=bar>diagram</svg></xml>",
            )
        )
    )

    # when
    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/a-file.puml",
                destination_abs="/tmp/dst/a-file.puml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/b-file",
                destination_abs="/tmp/dst/b-file",
            ),
        ],
    )

    # then
    assert len(operations) == 2
    assert operations[0].name() == "copy"
    assert operations[1].name() == "plantuml"

    # when
    operations[1].execute(fs)

    # then
    assert fs.files["/tmp/dst/a-file.svg"] == (
        "<xml><!-- @tech-docs-hash=0d0322fb363ceeb229d8"
        "ee7a9aec490ad5515bea0bf79743ac5898e48fa1737b --><svg foo=bar>diagram</svg></xml>"
    )


def test_swap_extension():
    assert swap_extension("foo/bar/baz.md", "svg") == "foo/bar/baz.svg"


def test_openapi_detector():
    fs = MockFilesystem(
        {
            "/tmp/Promil/api.yaml": """openapi: 3.1.0
paths:
    some-path: path""",
            "/tmp/Promil/invalid-api.yaml": "openapi: 3.1.0",
            "/tmp/Promil/other-file": "a-file-content",
            "/tmp/Promil/subdir/spec.json": '{"openapi": "3.1.0","paths": {"some-path": "path"}}',
            "/tmp/Promil/subdir/invalid-spec.json": '{"openapi": "3.1.0"}',
        }
    )
    detector = OpenAPIDetector(
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        )
    )

    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/api.yaml",
                destination_abs="/tmp/dst/api.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/invalid-api.yaml",
                destination_abs="/tmp/dst/invalid-api.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/other-file",
                destination_abs="/tmp/dst/other-file",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/spec.json",
                destination_abs="/tmp/dst/subdir/spec.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/invalid-spec.json",
                destination_abs="/tmp/dst/subdir/invalid-spec.json",
            ),
        ],
    )

    for operation in operations:
        print(operation.name(), operation.source_abs, operation.destination_abs)

    assert len(operations) == 5
    assert operations[0].name() == "copy"
    assert operations[1].name() == "copy"
    assert operations[2].name() == "copy"
    assert operations[3].name() == "openapi"
    assert operations[4].name() == "openapi"

    # when
    operations[3].execute(fs)
    operations[4].execute(fs)

    # then
    assert fs.files["/tmp/dst/api.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "f356dad852f2b8108be36a19c8e148c8b3ed5811c9bd072f2603d46c4aa4a0e6",
        },
        indent=2,
    )
    assert fs.files["/tmp/dst/subdir/spec.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "5891d4bf2471e070e3675a5eedc88fe724e572bc2053e7b2bf00fb3862cd4c8a",
        },
        indent=2,
    )
