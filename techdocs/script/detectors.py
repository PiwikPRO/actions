import copy
import re
from os import path

import nodes
from config import Config, ProjectDetailsReader
from index import FileIndex, FileIndexItem
from operations import (
    CopyOperation,
    DeleteOperation,
    DockerPlantUMLGenerator,
    PlantUMLDiagramRenderOperation,
)


class CopyDetector:
    def __init__(self, from_path: str, to_path: str, config: Config) -> None:
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
            relative_src, relative_dst = (
                file,
                path.join(rule.config.destination, path.basename(file)),
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
        return CopyOperation(
            source_abs=path.abspath(path.join(self.from_path, relative_src)),
            destination_abs=path.abspath(
                path.join(
                    self.to_path,
                    ProjectDetailsReader(self.to_path, fs).doc_path(rule.config.project),
                    relative_dst,
                ),
            ),
        )


class DefaultMatcher:
    def __init__(self, str_to_match):
        self.regex = re.escape(str_to_match).replace("\\*", ".*")

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
