import copy
import io
import json
import re
from os import path

import nodes
from config import Config, ProjectDetailsReader
from filesystem import Filesystem
from index import FileIndexItem
from operations import (
    DeleteOperation,
    DockerPlantUMLGenerator,
    GenericFileCopyOperation,
    OpenAPIValidator,
    PlantUMLDiagramRenderOperation,
    YAMLPrefaceEnrichingCopyOperation,
)
from operations import OpenAPIBundler, OpenAPIOperation


class CopyDetector:
    def __init__(
        self, from_path: str, to_path: str, author: str, branch: str, config: Config
    ) -> None:
        self.copy_rules = [
            Rule(
                document_rule,
                DefaultMatcher(document_rule.source),
                [DefaultMatcher(excluded) for excluded in document_rule.exclude],
            )
            for document_rule in config.documents
        ]
        self.from_path = from_path
        self.to_path = to_path
        self.author = author
        self.branch = branch

    def detect(self, fs, previous_operations):
        return [
            self._for_file(fs, file)
            for file in fs.scan(self.from_path, ".*")
            if self._for_file(fs, file) is not None
        ]

    def _for_file(self, fs, path: str):
        for rule in self.copy_rules:
            if rule.match(path):
                return self._create_operation(fs, path, rule)
        return None

    def _create_operation(self, fs, file, rule):
        if nodes.looks_fileish(rule.config.source) and nodes.looks_dirish(
            rule.config.destination
        ):
            destination_file = path.basename(file)
            if nodes.looks_globish(rule.config.source):
                source_base = rule.config.source.split("**/*")[0]
                destination_file = file.removeprefix(source_base)

            relative_src, relative_dst = (
                file,
                path.join(rule.config.destination, destination_file),
            )
        elif nodes.looks_fileish(rule.config.source) and nodes.looks_fileish(
            rule.config.destination
        ):
            relative_src, relative_dst = (
                file,
                rule.config.destination,
            )
        elif nodes.looks_dirish(rule.config.source) and nodes.looks_dirish(
            rule.config.destination
        ):
            relative_src, relative_dst = (
                file,
                path.join(rule.config.destination, file[len(rule.config.source) - 1 :]),
            )
        else:
            return None
        kwargs = dict(
            source_abs=path.abspath(path.join(self.from_path, relative_src)),
            destination_abs=path.abspath(
                path.join(
                    self.to_path,
                    ProjectDetailsReader(self.to_path, fs).doc_path(
                        rule.config.project
                    ),
                    relative_dst,
                ),
            ),
        )
        if any(
            [relative_src.endswith(suffix) for suffix in [".md", ".MD", ".mdx", ".MDX"]]
        ):
            return YAMLPrefaceEnrichingCopyOperation(
                **dict(
                    **kwargs,
                    from_abs=self.from_path,
                    author=self.author,
                    branch=self.branch,
                )
            )
        return GenericFileCopyOperation(**kwargs)


class DefaultMatcher:
    def __init__(self, str_to_match):
        # How to handle glob like **/* in the source
        self.regex = (re.escape(str_to_match).replace("\\*\\*/\\*", ".*")).replace(
            "\\*", "[^/]*"
        )

    def match(self, path):
        return re.match(self.regex, path) is not None


class Rule:
    def __init__(self, document_config_rule, matcher, excluders) -> None:
        self.config = document_config_rule
        self.matcher = matcher
        self.excluders = excluders

    def match(self, file):
        return self.matcher.match(file) and not (
            any([excluder.match(file) for excluder in self.excluders])
        )


class DeleteDetector:
    def __init__(self, repo, index, from_path, to_path) -> None:
        self.repo = repo
        self.index = index
        self.from_path = from_path
        self.to_path = to_path

    def detect(self, fs, previous_operations):
        child_result = previous_operations
        child_result_files_to_be_copied = [
            path.relpath(j, self.to_path)
            for sub in [o.destination_files() for o in child_result]
            for j in sub
        ]
        indexed_items = list([i for i in self.index.items if i.repo == self.repo])
        for item in indexed_items:
            if item.file not in child_result_files_to_be_copied:
                child_result.append(
                    DeleteOperation(
                        path.abspath(
                            path.join(self.to_path, item.file),
                        )
                    )
                )
                self.index.remove(item)

        for item in child_result_files_to_be_copied:
            self.index.add(FileIndexItem(item, self.repo))
        return child_result


class UnnecessaryOperationsFilteringDetector:
    def detect(self, fs, previous_operations):
        return list(filter(lambda op: op.has_changes(fs), previous_operations))


class PlantUMLDiagramsDetector:
    def __init__(self, generator=None):
        self.generator = generator or DockerPlantUMLGenerator()

    def detect(self, fs, previous_operations):
        pumls = list(
            filter(
                lambda op: any([f.endswith(".puml") for f in op.source_files()]),
                previous_operations,
            )
        )
        return list(
            filter(
                lambda op: not any([f.endswith(".puml") for f in op.source_files()]),
                previous_operations,
            )
        ) + [
            PlantUMLDiagramRenderOperation(
                puml.source_abs,
                swap_extension(puml.destination_abs, "svg"),
                self.generator,
            )
            for puml in pumls
        ]


def swap_extension(file_path: str, new_extension: str) -> str:
    base_name = path.splitext(file_path)[0]
    return f"{base_name}.{new_extension}"


class OperationDetectorChain:
    def __init__(self, *detectors):
        self.detectors = detectors

    def operations(self, fs):
        operations = []
        for detector in self.detectors:
            operations = detector.detect(fs, copy.deepcopy(operations))
        return operations


class OpenAPIFile:
    def __init__(self, source_abs, destination_abs, ref_files):
        self.source_abs = source_abs
        self.destination_abs = destination_abs
        self.ref_files = ref_files


class OpenAPIDetector:
    def __init__(self, bundler=None, validator=None):
        self.bundler = bundler or OpenAPIBundler()
        self.validator = validator or OpenAPIValidator()

    def _detect_yaml_files(self, fs, previous_operations):
        yaml_files = [
            op
            for op in previous_operations
            if any(f.endswith((".yaml", ".yml")) for f in op.source_files())
        ]
        openapi_spec_files = []
        for yaml_file in yaml_files:
            file = io.StringIO(fs.read_string(yaml_file.source_abs))
            if file.readline().startswith("openapi:"):
                if any(line.startswith("paths:\n") for line in file):
                    yaml_file.destination_abs = yaml_file.destination_abs.replace(
                        ".yaml", ".json"
                    ).replace(".yml", ".json")
                    openapi_spec_files.append(
                        OpenAPIFile(
                            yaml_file.source_abs,
                            yaml_file.destination_abs,
                            self._detect_referenced_files_yaml(fs, yaml_file),
                        )
                    )
        return openapi_spec_files

    @staticmethod
    def _detect_referenced_files_yaml(fs, openapi_file):
        ref_files = [
            re.search(r"\$ref:\s+[\'\"]?([.a-z_\-/]+)", line).group(1)
            for line in fs.read_string(openapi_file.source_abs).split("\n")
            if "$ref" in line
        ]
        return [
            path.abspath(path.join(path.dirname(openapi_file.source_abs), ref_file))
            for ref_file in ref_files
        ]

    def _detect_json_files(self, fs, previous_operations):
        json_files = [
            op
            for op in previous_operations
            if any(f.endswith(".json") for f in op.source_files())
        ]
        openapi_spec_files = []
        for json_file in json_files:
            file = json.loads(fs.read_string(json_file.source_abs))
            if isinstance(file, dict) and file.get("openapi") and file.get("paths"):
                openapi_spec_files.append(
                    OpenAPIFile(
                        json_file.source_abs,
                        json_file.destination_abs,
                        self._detect_referenced_files_json(fs, json_file),
                    )
                )
        return openapi_spec_files

    @staticmethod
    def _detect_referenced_files_json(fs, openapi_file):
        ref_files = []
        data = json.loads(fs.read_string(openapi_file.source_abs))

        def look_for_files_in_refs(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "$ref":
                        ref_files.append(re.search(r"([.a-z_\-/]+)", value).group(1))
                    else:
                        look_for_files_in_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    look_for_files_in_refs(item)

        look_for_files_in_refs(data)
        return [
            path.abspath(path.join(path.dirname(openapi_file.source_abs), ref_file))
            for ref_file in ref_files
        ]

    def detect(self, fs: Filesystem, previous_operations):
        openapi_spec_files = self._detect_yaml_files(
            fs, previous_operations
        ) + self._detect_json_files(fs, previous_operations)
        return [
            op
            for op in previous_operations
            if op.source_abs not in [spec.source_abs for spec in openapi_spec_files]
        ] + [
            OpenAPIOperation(
                spec.source_abs,
                spec.destination_abs,
                spec.ref_files,
                self.bundler,
                self.validator,
                previous_operations,
            )
            for spec in openapi_spec_files
        ]
