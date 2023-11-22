import os
import shutil
import subprocess
import tempfile
from hashlib import sha256


class CopyOperation:
    def __init__(self, source_abs, destination_abs):
        self.source_abs = source_abs
        self.destination_abs = destination_abs

    def name(self):
        return "copy"

    def execute(self, fs):
        fs.copy(self.source_abs, self.destination_abs)

    def has_changes(self, fs):
        if (not fs.is_file(self.destination_abs)) or hashb(fs.read_bytes(self.source_abs)) != hashb(
            fs.read_bytes(self.destination_abs)
        ):
            return True
        return False

    def source_files(self):
        return [self.source_abs]

    def destination_files(self):
        return [self.destination_abs]

    def mkd(self, path_formatter):
        return f"* [COPY] {path_formatter.format(self.source_abs)} -> {path_formatter.format(self.destination_abs)}"


class DeleteOperation:
    def __init__(self, destination_abs):
        self.destination_abs = destination_abs

    def name(self):
        return "delete"

    def execute(self, fs):
        fs.delete(self.destination_abs)

    def source_files(self):
        return []

    def destination_files(self):
        return []

    def has_changes(self, fs):
        return True

    def mkd(self, path_formatter):
        return f"* [DELETE] {path_formatter.format(self.destination_abs)}"


class PlantUMLDiagramRenderOperation:
    def __init__(self, source_puml_abs, destination_svg_abs, generator):
        self.source_puml_abs = source_puml_abs
        self.destination_svg_abs = destination_svg_abs
        self.generator = generator

    def name(self):
        return "plantuml"

    def execute(self, fs):
        fs.write_string(
            self.destination_svg_abs,
            self.generator.generate(fs, self.source_puml_abs).replace(
                "<svg ", self.header(fs) + "<svg "
            ),
        )

    def source_files(self):
        return [self.source_puml_abs]

    def destination_files(self):
        return [self.destination_svg_abs]

    def has_changes(self, fs):
        if not fs.is_file(self.destination_svg_abs):
            return True
        return self.header(fs) not in fs.read_string(self.destination_svg_abs)

    def header(self, fs):
        return header(hashb(get_full_puml_content(fs, self.source_puml_abs)))

    def mkd(self, path_formatter):
        return f"* [PLANTUML] {path_formatter.format(self.source_puml_abs)} -> {path_formatter.format(self.destination_svg_abs)}"


def header(hash):
    return "<!-- @tech-docs-hash=" + hash + " -->"


def hashb(data):
    return sha256(data).hexdigest()


def get_full_puml_content(fs, the_path):
    content = fs.read_bytes(the_path)
    lines = content.split(b"\n")
    for i, line in enumerate(lines):
        if line.startswith(b"!include ") and b"http://" not in line and b"https://" not in line:
            lines[i] = get_full_puml_content(
                fs, os.path.join(os.path.dirname(the_path), line.split(b"!include ")[1].decode())
            )
    return b"\n".join(lines)


class DockerPlantUMLGenerator:
    def generate(self, fs, source_puml_abs):
        try:
            dirpath = tempfile.mkdtemp()
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-v",
                    f"{os.path.dirname(source_puml_abs)}:/src",
                    "-v",
                    f"{dirpath}:/out",
                    "ghcr.io/plantuml/plantuml:1",
                    f"/src/{os.path.basename(source_puml_abs)}",
                    "-o",
                    "/out",
                    "-tsvg",
                ]
            )
            generated_files = fs.scan(dirpath, ".*")
            if len(generated_files) != 1:
                raise Exception("PlantUML generation failed")
            with open(os.path.join(dirpath, generated_files[0]), "r") as f:
                return f.read()
        finally:
            shutil.rmtree(dirpath)
