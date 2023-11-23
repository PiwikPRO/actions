import json
import os
import subprocess

import pytest
from filesystem import Filesystem


def prepare_fs(files):
    fs = Filesystem()
    for file in files:
        fs.write_string(file, files[file])


def test_integration(tmp_path):
    prepare_fs(
        {
            os.path.join(tmp_path, k): v
            for k, v in {
                "src/README.md": "readme",
                "src/docs/one.md": "one",
                "src/docs/two.txt": "two",
                "dst/projects.json": json.dumps({"promil": {"path": "docs/promil"}}),
                "config.json": json.dumps(
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
                                    "docs/*.txt",
                                ],
                            },
                        ],
                    }
                ),
            }.items()
        }
    )
    assert (
        subprocess.run(
            [
                "python",
                "cli.py",
                "copy",
                "--from",
                os.path.join(tmp_path, "src"),
                "--to",
                os.path.join(tmp_path, "dst"),
                "--config",
                os.path.join(tmp_path, "config.json"),
                "--index",
                "promil",
            ]
        ).returncode
        == 0
    )
    assert os.path.exists(os.path.join(tmp_path, "dst/docs/promil/bla.md"))
    assert os.path.exists(os.path.join(tmp_path, "dst/docs/promil/somedir/one.md"))
    assert not os.path.exists(os.path.join(tmp_path, "dst/docs/promil/somedir/two.txt"))
