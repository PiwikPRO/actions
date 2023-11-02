from unittest.mock import Mock

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from operations import Detector
from config import Config


@pytest.mark.parametrize(
    'file,rule_source,rule_destination,expected_source,expected_destination',
    (
        ( # if source is a file, destination a directory, copy the file directly into the directory
            "docs/promil/foo.md", 
            "docs/promil/foo.md", 
            "docs/promil/stacks/Promil-stack-analytics", 
            "/home/foobar/docs/promil/foo.md", 
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/foo.md",
        ),
        ( # if source is a directory, destination a directory, copy the directory into the directory, 
          # recursively, including the subdirectory structure
            "docs/promil/bla/huehue/foo.md", 
            "docs/*", 
            "docs/promil/stacks/Promil-stack-analytics", 
            "/home/foobar/docs/promil/bla/huehue/foo.md", 
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/promil/bla/huehue/foo.md",
        ),
        ( # if source is a file, destination a file, copy the file directly into the file
            "docs/promil/foo.md", 
            "docs/promil/foo.md", 
            "docs/promil/stacks/Promil-stack-analytics/bar.md", 
            "/home/foobar/docs/promil/foo.md", 
            "/tmp/Tech-docs/docs/promil/stacks/Promil-stack-analytics/bar.md",
        ),
    )
)
def test_copy_create_operation(file,rule_source,rule_destination,expected_source,expected_destination):
    detector = Detector("/home/foobar", "/tmp/Tech-docs", Config("", []))
    copy_operation = detector._create_operation(
        file,
        Mock(
            config=Mock(
                source=rule_source,
                destination=rule_destination,
            )
        ),
    )
    assert copy_operation.source_abs == expected_source
    assert (
        copy_operation.destination_abs
        == expected_destination
    )
