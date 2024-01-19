import pytest

from frontmatter import FrontmatterEnricher, source_frontmatter_hash


@pytest.mark.parametrize(
    "doc, expected",
    (
        (  # If there is no frontmatter, add it
            """# foo
bar
baz
""",
            """---
foo: bar
---
# foo
bar
baz
""",
        ),
        (  # If there is frontmatter, append new attributes
            """---
bla: bla
---
# foo
bar
baz
""",
            """---
bla: bla
foo: bar
---
# foo
bar
baz
""",
        ),
    ),
)
def test_enricher_enrich(doc, expected):
    assert expected == FrontmatterEnricher(doc).enrich(
        lambda *args: "foo: bar\n",
    )


@pytest.mark.parametrize(
    "doc, expected",
    (
        (  # If there is frontmatter, remove it
            """---
bla: bla
---
# foo
bar
baz
""",
            """# foo
bar
baz
""",
        ),
        (  # If there is no frontmatter, do nothing
            """# foo
bar
baz
""",
            """# foo
bar
baz
""",
        ),
    ),
)
def test_enricher_strip(doc, expected):
    assert expected == FrontmatterEnricher(doc).strip()


@pytest.mark.parametrize(
    "doc, expected",
    (
        (  # If there is frontmatter, calculate its hash
            """---
bla: bla
---
# foo
bar
baz
""",
            """---
bla: bla
x_source_frontmatter_hash: 84856eef997d316c276d76c25d4caa3e467cab5bbdc5d59c3e52442a54feb15b
---
# foo
bar
baz
""",
        ),
        (  # If there is no frontmatter, do nothing
            """# foo
bar
baz
""",
            """# foo
bar
baz
""",
        ),
    ),
)
def test_source_frontmatter_hash_calculated(doc, expected):
    assert expected == FrontmatterEnricher(doc).enrich(
        source_frontmatter_hash(doc),
    )
