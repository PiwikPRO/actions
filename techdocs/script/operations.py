import json
import os
import shutil
import subprocess
import tempfile

from frontmatter import (
    FrontmatterEnricher,
    custom_edit_url,
    get_source_frontmatter_hash,
    last_update,
    source_frontmatter_hash,
)
from hash import hashb


class GenericFileCopyOperation:
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


class YAMLPrefaceEnrichingCopyOperation:
    def __init__(self, source_abs, destination_abs, from_abs, author, branch):
        self.source_abs = source_abs
        self.destination_abs = destination_abs
        self.author = author
        self.branch = branch
        self.from_abs = os.path.abspath(from_abs)
        self.repo = os.path.basename(self.from_abs)

    def name(self):
        return "copy"

    def execute(self, fs):
        source_file = fs.read_string(self.source_abs)
        new_content = FrontmatterEnricher(source_file).enrich(
            custom_edit_url(
                self.repo, os.path.relpath(self.source_abs, self.from_abs), self.branch
            ),
            last_update(self.author),
            # save the hash of the source frontmatter, so we can detect changes later
            source_frontmatter_hash(source_file),
            lambda *args: "x_tech_docs_enriched: true\n",
        )
        fs.write_string(self.destination_abs, new_content)

    def has_changes(self, fs):
        dest_file = fs.read_string(self.destination_abs) if fs.is_file(self.destination_abs) else ""
        source_file = fs.read_string(self.source_abs)

        if any(
            [
                not fs.is_file(self.destination_abs),
                file_has_no_frontmatter(fs, dest_file),
                files_content_ignoring_frontmatter_is_different(fs, source_file, dest_file),
                source_frontmatter_hash_is_different_than_one_cached_in_destination(
                    fs, source_file, dest_file
                ),
            ]
        ):
            return True
        return False

    def source_files(self):
        return [self.source_abs]

    def destination_files(self):
        return [self.destination_abs]

    def mkd(self, path_formatter):
        return f"* [COPY] {path_formatter.format(self.source_abs)} -> {path_formatter.format(self.destination_abs)}"


def file_has_no_frontmatter(fs, file):
    return "x_tech_docs_enriched: true" not in file


def files_content_ignoring_frontmatter_is_different(fs, first_file, second_file):
    return hashb(FrontmatterEnricher(first_file).strip().encode()) != hashb(
        FrontmatterEnricher(second_file).strip().encode()
    )


def source_frontmatter_hash_is_different_than_one_cached_in_destination(
    fs, source_file, destination_file
):
    return source_file.startswith("---") and hashb(
        source_file.split("---\n")[1].encode()
    ) != get_source_frontmatter_hash(destination_file)


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
        return (
            f"* [PLANTUML] {path_formatter.format(self.source_puml_abs)} -> "
            f"{path_formatter.format(self.destination_svg_abs)}"
        )


def header(hash):
    return "<!-- @tech-docs-hash=" + hash + " -->"


def get_full_puml_content(fs, the_path):
    content = fs.read_bytes(the_path)
    lines = content.split(b"\n")
    for i, line in enumerate(lines):
        if line.startswith(b"!include ") and b"http://" not in line and b"https://" not in line:
            try:
                lines[i] = get_full_puml_content(
                    fs,
                    os.path.join(os.path.dirname(the_path), line.split(b"!include ")[1].decode()),
                )
            except (
                FileNotFoundError
            ):  # Let PlantUML handle the error, also we don't need to hack 10 ifs with various import syntaxes here
                pass
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


class OpenAPIOperation:
    def __init__(self, source_abs, destination_abs, bundler):
        self.source_abs = source_abs
        self.destination_abs = destination_abs
        self.bundler = bundler

    def name(self):
        return "openapi"

    def execute(self, fs):
        checksum = hashb(fs.read_string(self.source_abs).encode())
        bundled_content = json.loads(self.bundler.bundle(fs, self.source_abs, self.destination_abs))
        bundled_content["x-api-checksum"] = checksum

        fs.write_string(self.destination_abs, json.dumps(bundled_content, indent=2))

    def has_changes(self, fs):
        if not fs.is_file(self.destination_abs):
            return True
        return not self.valid_checksum(fs, self.source_abs, self.destination_abs)

    def source_files(self):
        return [self.source_abs]

    def destination_files(self):
        return [self.destination_abs]

    def mkd(self, path_formatter):
        return f"* [OPENAPI] {path_formatter.format(self.source_abs)} -> {path_formatter.format(self.destination_abs)})"

    def valid_checksum(self, fs, source_abs, destination_abs):
        source_checksum = hashb(fs.read_string(source_abs).encode())
        with open(destination_abs, "r") as f:
            destination_checksum = json.loads(f.read())["x-api-checksum"]
        return source_checksum == destination_checksum


class OpenAPIBundler:
    def bundle(self, fs, source_abs, destination_abs):
        try:
            dir_path = tempfile.mkdtemp()
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-v",
                    f"{os.path.dirname(source_abs)}:/spec",
                    "-v",
                    f"{dir_path}:/out",
                    "redocly/cli",
                    "bundle",
                    "--dereferenced",
                    f"/spec/{os.path.basename(source_abs)}",
                    "--output",
                    f"/out/{os.path.basename(destination_abs)}",
                    "--ext",
                    "json",
                ]
            )
            generated_files = fs.scan(dir_path, ".*")
            if len(generated_files) != 1:
                raise Exception("OpenAPI generation failed")
            with open(os.path.join(dir_path, generated_files[0]), "r") as f:
                return f.read()
        finally:
            shutil.rmtree(dir_path)
