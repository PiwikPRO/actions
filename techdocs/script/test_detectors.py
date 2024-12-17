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
            "/foo/index/Promil-platform-foo/42af564a885e1f38be3f411de2584efc3462bba68e9b5ea6dc39364b061d0a8f": json.dumps(
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


def test_openapi_detector_json():
    fs = MockFilesystem(
        {
            "/tmp/Promil/other-file": "a-file-content",
            "/tmp/Promil/subdir/spec.json": '{"openapi": "3.1.0","paths": {"some-path": "path"}}',
            "/tmp/Promil/subdir/other.json": '{"some": "attribute"}',
            "/tmp/Promil/nested-components.json": '{"openapi": "3.1.0", "some-component": "nested-component"}',
            "/tmp/Promil/components.json": '{"openapi": "3.1.0", "components": {"$ref": "nested-components.json#/some-component"}}',
            "/tmp/Promil/subdir/spec-with-ref.json": '{"openapi": "3.1.0","paths": {"$ref": "../components.json#/some-component"}}',
            "/tmp/Promil/subdir/spec-with-local-ref.json": '{"openapi": "3.1.0","paths": {"$ref": "../components.json#/some-component"}}',
        }
    )
    detector = OpenAPIDetector(
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
    )

    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/other-file",
                destination_abs="/tmp/dst/other-file",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/spec.json",
                destination_abs="/tmp/dst/subdir/spec.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/other.json",
                destination_abs="/tmp/dst/subdir/other.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/components.json",
                destination_abs="/tmp/dst/components.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/nested-components.json",
                destination_abs="/tmp/dst/nested-components.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/spec-with-ref.json",
                destination_abs="/tmp/dst/subdir/spec-with-ref.json",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/spec-with-local-ref.json",
                destination_abs="/tmp/dst/subdir/spec-with-local-ref.json",
            ),
        ],
    )

    assert len(operations) == 7
    assert operations[0].name() == "copy"
    assert operations[1].name() == "copy"
    assert operations[2].name() == "copy"
    assert operations[3].name() == "copy"

    assert operations[4].name() == "openapi"
    assert operations[4].ref_files == []
    assert operations[5].name() == "openapi"
    assert sorted(operations[5].ref_files) == [
        "/tmp/Promil/components.json",
        "/tmp/Promil/nested-components.json",
    ]
    assert operations[6].name() == "openapi"
    assert sorted(operations[6].ref_files) == [
        "/tmp/Promil/components.json",
        "/tmp/Promil/nested-components.json",
    ]

    # when
    operations[4].execute(fs)
    operations[5].execute(fs)
    operations[6].execute(fs)

    # then
    assert fs.files["/tmp/dst/subdir/spec.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "5891d4bf2471e070e3675a5eedc88fe724e572bc2053e7b2bf00fb3862cd4c8a",
        },
        indent=2,
    )
    assert fs.files["/tmp/dst/subdir/spec-with-ref.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "ab740669e63a90c75c3192818aa5c6a820ce71a8f53aa84354dad77183e27730",
        },
        indent=2,
    )
    assert fs.files["/tmp/dst/subdir/spec-with-local-ref.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "ab740669e63a90c75c3192818aa5c6a820ce71a8f53aa84354dad77183e27730",
        },
        indent=2,
    )


def test_openapi_detector_yaml():
    fs = MockFilesystem(
        {
            "/tmp/Promil/api.yaml": """openapi: 3.1.0
paths:
    some-path: path""",
            "/tmp/Promil/components.yaml": "openapi: 3.1.0",
            "/tmp/Promil/some-other.yaml": "some: attribute",
            "/tmp/Promil/other-file": "a-file-content",
            "/tmp/Promil/subdir/api-with-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: ../components.yaml#/some-component""",
            "/tmp/Promil/subdir/api-with-local-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: #/some-component""",
        }
    )
    detector = OpenAPIDetector(
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
    )

    operations = detector.detect(
        fs,
        [
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/api.yaml",
                destination_abs="/tmp/dst/api.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/components.yaml",
                destination_abs="/tmp/dst/components.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/some-other.yaml",
                destination_abs="/tmp/dst/some-other.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/other-file",
                destination_abs="/tmp/dst/other-file",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/api-with-ref.yaml",
                destination_abs="/tmp/dst/subdir/api-with-ref.yaml",
            ),
            GenericFileCopyOperation(
                source_abs="/tmp/Promil/subdir/api-with-local-ref.yaml",
                destination_abs="/tmp/dst/subdir/api-with-local-ref.yaml",
            ),
        ],
    )

    assert len(operations) == 6
    assert operations[0].name() == "copy"
    assert operations[1].name() == "copy"
    assert operations[2].name() == "copy"
    assert operations[3].name() == "openapi"
    assert operations[3].ref_files == []
    assert operations[4].name() == "openapi"
    assert operations[4].ref_files == ["/tmp/Promil/components.yaml"]
    assert operations[5].name() == "openapi"
    assert operations[5].ref_files == []

    # when
    operations[3].execute(fs)
    operations[4].execute(fs)
    operations[5].execute(fs)

    # then
    assert fs.files["/tmp/dst/api.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "f356dad852f2b8108be36a19c8e148c8b3ed5811c9bd072f2603d46c4aa4a0e6",
        },
        indent=2,
    )
    assert fs.files["/tmp/dst/subdir/api-with-ref.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "d1ff36ee679797e54a3c6e7858e70cfabcb642641fa14f614b173d439f9d3642",
        },
        indent=2,
    )
    assert fs.files["/tmp/dst/subdir/api-with-local-ref.json"] == json.dumps(
        {
            "itsa me": "openapi",
            "x-api-checksum": "9d02b4bf2b95c5617f7cb10ef16cc881793b2cf08486b04163aa948f10002822",
        },
        indent=2,
    )
