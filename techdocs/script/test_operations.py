import json

import pytest

from filesystem import MockFilesystem
from operations import YAMLPrefaceEnrichingCopyOperation


def test_yaml_preface_operation(filesystem):
    op = YAMLPrefaceEnrichingCopyOperation(
        "/tmp/foo/README.md",
        "/tmp/bar/README.md",
        "/tmp/foo",
        "Χάρις Αλεξίου",
        "master",
    )

    op.execute(filesystem)

    assert "https://github.com/PiwikPRO/foo/edit/master/README.md" in filesystem.read_string(
        "/tmp/bar/README.md"
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
