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
        if nodes.looks_fileish(rule.config.source) and nodes.looks_dirish(rule.config.destination):
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
        elif nodes.looks_dirish(rule.config.source) and nodes.looks_dirish(rule.config.destination):
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
                    ProjectDetailsReader(self.to_path, fs).doc_path(rule.config.project),
                    relative_dst,
                ),
            ),
        )
        if any([relative_src.endswith(suffix) for suffix in [".md", ".MD", ".mdx", ".MDX"]]):
            return YAMLPrefaceEnrichingCopyOperation(
                **dict(**kwargs, from_abs=self.from_path, author=self.author, branch=self.branch)
            )
        return GenericFileCopyOperation(**kwargs)


class DefaultMatcher:
    def __init__(self, str_to_match):
        print(str_to_match)
        # How to handle glob like **/* in the source
        self.regex = (re.escape(str_to_match).replace("\\*\\*/\\*", ".*")).replace("\\*", "[^/]*")

    def match(self, path):
        print(f"Path: {path}  Regex:{self.regex}")
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


class OpenAPIDetector:
    def __init__(self, bundler=None):
        self.bundler = bundler or OpenAPIBundler()

    def _detect_yaml_files(self, fs, previous_operations):
        yaml_files = list(
            filter(
                lambda op: any(
                    [f.endswith(".yaml") or f.endswith(".yml") for f in op.source_files()]
                ),
                previous_operations,
            )
        )
        openapi_spec_files = []
        for yaml_file in yaml_files:
            file = io.StringIO(fs.read_string(yaml_file.source_abs))
            first_line = file.readline()
            if first_line.startswith("openapi:"):
                for line in file:
                    if line.startswith("paths:\n"):
                        yaml_file.destination_abs = self._prepare_destination(
                            yaml_file.destination_abs
                        )
                        openapi_spec_files.append(yaml_file)
                        break
        return openapi_spec_files

    def _detect_json_files(self, fs, previous_operations):
        json_files = list(
            filter(
                lambda op: any([f.endswith(".json") for f in op.source_files()]),
                previous_operations,
            )
        )
        openapi_spec_files = []
        for json_file in json_files:
            file = json.loads(fs.read_string(json_file.source_abs))
            if isinstance(file, dict) and file.get("openapi") and len(file.get("paths", [])) > 0:
                json_file.destination_abs = self._prepare_destination(json_file.destination_abs)
                openapi_spec_files.append(json_file)
        return openapi_spec_files

    def _prepare_destination(self, source):
        source = source.replace(".yaml", ".json").replace(".yml", ".json")
        return source

    def detect(self, fs: Filesystem, previous_operations):
        openapi_spec_files = self._detect_yaml_files(
            fs, previous_operations
        ) + self._detect_json_files(fs, previous_operations)

        return list(
            filter(
                lambda op: op not in openapi_spec_files,
                previous_operations,
            )
        ) + [
            OpenAPIOperation(
                openapi_spec.source_abs,
                openapi_spec.destination_abs,
                self.bundler,
            )
            for openapi_spec in openapi_spec_files
        ]
