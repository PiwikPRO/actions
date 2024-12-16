import json
from unittest.mock import Mock

import pytest

from filesystem import MockFilesystem
from operations import PlantUMLDiagramRenderOperation, YAMLPrefaceEnrichingCopyOperation
from techdocs.script.operations import GenericFileCopyOperation, OpenAPIOperation


def test_yaml_preface_operation(filesystem):
    op = YAMLPrefaceEnrichingCopyOperation(
        "/tmp/foo/README.md",
        "/tmp/bar/README.md",
        "/tmp/foo",
        "Χάρις Αλεξίου",
        "master",
    )

    op.execute(filesystem)

    assert (
        "https://github.com/PiwikPRO/foo/edit/master/README.md"
        in filesystem.read_string("/tmp/bar/README.md")
    )


@pytest.mark.parametrize(
    "source, destination, expected",
    (
        ("#foo", "#foo", True),  # lacks x_tech_docs_enriched
        (
            "#foo\n",
            """---
foo: bar
x_tech_docs_enriched: true
---
#foo
""",
            False,
        ),  # content is the same and source does not have frontmatter
        (
            """---
foo: bar
---
#foo
""",
            """---
foo: bar
x_tech_docs_enriched: true
---
#foo
""",
            True,  # content is the same, there is no source frontmatter hash in destination
        ),
        (
            """---
foo: bar
---
#foo
""",
            """---
foo: bar
x_source_frontmatter_hash: 84856eef997d316c276d76c25d4caa3e467cab5bbdc5d59c3e52442a54feb15b
x_tech_docs_enriched: true
---
#foo
""",
            True,  # content is the same, source frontmatter hash does not match source frontmatter content
        ),
        (
            """---
foo: bar
---
#foo
""",
            """---
foo: bar
x_source_frontmatter_hash: 1dabc4e3cbbd6a0818bd460f3a6c9855bfe95d506c74726bc0f2edb0aecb1f4e
x_tech_docs_enriched: true
---
#foo
""",
            False,  # content is the same, source frontmatter hash does not match source frontmatter content
        ),
    ),
)
def test_yaml_preface_has_changes(source, destination, expected):
    filesystem = MockFilesystem(
        {
            "/tmp/techdocs/config.json": json.dumps(
                {
                    "documents": [
                        {
                            "project": "promil",
                            "source": "docs/*",
                            "destination": "docs/",
                        },
                    ],
                }
            ),
            "/tmp/foo/README.md": source,
            "/tmp/bar/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
            "/tmp/bar/README.md": destination,
        }
    )

    op = YAMLPrefaceEnrichingCopyOperation(
        "/tmp/foo/README.md",
        "/tmp/bar/README.md",
        "/tmp/foo",
        "Χάρις Αλεξίου",
        "master",
    )

    assert op.has_changes(filesystem) == expected


def test_openapi_operation_has_changes_no_changes():
    fs = MockFilesystem(
        {
            "/tmp/Promil/components.yaml": "openapi: 3.1.0",
            "/tmp/Promil/subdir/api-with-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: ../components.json#/some-component""",
            "/tmp/dst/subdir/api-with-ref.json": '{"x-api-checksum": "efb49e76308ecfad18ff3dcaadad6eade83b07de82e56be4322897038ebb44e2"}',
        }
    )
    operation = OpenAPIOperation(
        "/tmp/Promil/subdir/api-with-ref.yaml",
        "/tmp/dst/subdir/api-with-ref.json",
        ["/tmp/Promil/components.yaml"],
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
        previous_operations=[],
    )

    assert not operation.has_changes(fs)


def test_openapi_operation_has_changes_different_checksum():
    fs = MockFilesystem(
        {
            "/tmp/Promil/components.yaml": "openapi: 3.1.0",
            "/tmp/Promil/subdir/api-with-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: ../components.json#/some-component""",
            "/tmp/dst/subdir/api-with-ref.json": '{"x-api-checksum": "checksum-mismatch"}',
        }
    )
    operation = OpenAPIOperation(
        "/tmp/Promil/subdir/api-with-ref.yaml",
        "/tmp/dst/subdir/api-with-ref.json",
        ["/tmp/Promil/components.yaml"],
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
        previous_operations=[],
    )

    assert operation.has_changes(fs)


def test_openapi_operation_has_changes_ref_file_copy_operation():
    fs = MockFilesystem(
        {
            "/tmp/Promil/components.yaml": "openapi: 3.1.0",
            "/tmp/Promil/subdir/api-with-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: ../components.json#/some-component""",
            "/tmp/dst/subdir/api-with-ref.json": '{"x-api-checksum": "efb49e76308ecfad18ff3dcaadad6eade83b07de82e56be4322897038ebb44e2"}',
        }
    )
    operation = OpenAPIOperation(
        "/tmp/Promil/subdir/api-with-ref.yaml",
        "/tmp/dst/subdir/api-with-ref.json",
        ["/tmp/Promil/components.yaml"],
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
        previous_operations=[
            GenericFileCopyOperation(
                "/tmp/Promil/components.yaml",
                "/tmp/dst/components.yaml",
            )
        ],
    )

    assert operation.has_changes(fs)


def test_openapi_operation_has_changes_ref_file_other_operation():
    fs = MockFilesystem(
        {
            "/tmp/Promil/components.yaml": "openapi: 3.1.0",
            "/tmp/Promil/subdir/api-with-ref.yaml": """openapi: 3.1.0
paths:
    some-path:
        $ref: ../components.json#/some-component""",
            "/tmp/dst/subdir/api-with-ref.json": '{"x-api-checksum": "efb49e76308ecfad18ff3dcaadad6eade83b07de82e56be4322897038ebb44e2"}',
        }
    )
    operation = OpenAPIOperation(
        "/tmp/Promil/subdir/api-with-ref.yaml",
        "/tmp/dst/subdir/api-with-ref.json",
        ["/tmp/Promil/components.yaml"],
        bundler=Mock(
            bundle=Mock(
                return_value='{"itsa me":"openapi"}',
            )
        ),
        validator=Mock(return_value=True),
        previous_operations=[
            PlantUMLDiagramRenderOperation(
                "/tmp/Promil/components.yaml", "/tmp/dst/components.yaml", None
            )
        ],
    )

    assert not operation.has_changes(fs)
