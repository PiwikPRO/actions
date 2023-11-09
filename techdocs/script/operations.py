import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from os import path

import nodes
from config import Config, ProjectDetailsReader


@dataclass
class FilesystemOperation:
    TYPE_COPY = "copy"
    TYPE_DELETE = "delete"

    type: str
    source_abs: str
    destination_abs: str

    def __str__(self):
        if self.type == FilesystemOperation.TYPE_COPY:
            return "Copy file {} to {}".format(self.source_abs, self.destination_abs)
        elif self.type == FilesystemOperation.TYPE_DELETE:
            return "Delete file {}".format(self.source_abs)
        else:
            return "Unknown operation"


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

    def detect(self, filesystem):
        return [
            self._for_file(filesystem, file)
            for file in filesystem.scan(self.from_path, ".*")
            if self._for_file(filesystem, file) is not None
        ]

    def _for_file(self, filesystem, path: str):
        for rule in self.copy_rules:
            if rule.match(path):
                return self._create_operation(filesystem, path, rule)
        return None

    def _create_operation(self, filesystem, file, rule):
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
        return FilesystemOperation(
            type=FilesystemOperation.TYPE_COPY,
            source_abs=path.abspath(path.join(self.from_path, relative_src)),
            destination_abs=path.abspath(
                path.join(
                    self.to_path,
                    ProjectDetailsReader(self.to_path, filesystem).doc_path(rule.config.project),
                    relative_dst,
                ),
            ),
        )


class DeleteDetector:
    def __init__(self, repo, index, from_path, to_path, child) -> None:
        self.repo = repo
        self.index = index
        self.from_path = from_path
        self.to_path = to_path
        self.child = child

    def detect(self, filesystem):
        child_result = self.child.detect(filesystem)
        child_result_files_to_be_copied = [
            path.relpath(op.destination_abs, self.to_path)
            for op in child_result
            if op.type == FilesystemOperation.TYPE_COPY
        ]
        indexed_items = list([i for i in self.index.items if i.repo == self.repo])
        for item in indexed_items:
            if item.file not in child_result_files_to_be_copied:
                child_result.append(
                    FilesystemOperation(
                        type=FilesystemOperation.TYPE_DELETE,
                        source_abs=path.abspath(
                            path.join(self.to_path, item.file),
                        ),
                        destination_abs=None,
                    )
                )
                self.index.remove(item)

        for item in child_result_files_to_be_copied:
            self.index.add(FileIndexItem(item, self.repo))
        return child_result


def hash(some_str):
    return sha256(some_str.encode()).hexdigest()


def hashb(data):
    return sha256(data).hexdigest()


class UnnecessaryOperationsFilteringDetector:
    def __init__(self, child) -> None:
        self.child = child

    def detect(self, filesystem):
        return list(filter(self.requires_changes_on_fs(filesystem), self.child.detect(filesystem)))

    def requires_changes_on_fs(self, filesystem):
        def inner(operation):
            if operation.type == operation.TYPE_DELETE:
                return True
            if (not filesystem.is_file(operation.destination_abs)) or hashb(
                filesystem.read_bytes(operation.source_abs)
            ) != hashb(filesystem.read_bytes(operation.destination_abs)):
                return True
            return False

        return inner


class FileIndex:
    def __init__(self, items: tuple):
        self.items = items
        self.removed = ()

    def add(self, item):
        for existing_item in self.items:
            # If it's not the same file, keep looking
            if item.file != existing_item.file:
                continue
            # If it's the same file coming from the same repo, do nothing, just return
            if item.repo == existing_item.repo:
                return
            # If it's the same file coming from a different repo, raise an error
            raise FileIndexError(
                f"The file {item.file} is already indexed from repository {existing_item.repo}"
            )
        # If the loop ends, it means the file is not indexed yet, so add it
        self.items = self.items + (item,)

    def remove(self, item):
        removed = tuple(filter(lambda existing_item: existing_item.file == item.file, self.items))
        self.items = tuple(
            filter(lambda existing_item: existing_item.file != item.file, self.items)
        )
        self.removed = self.removed + removed


@dataclass
class FileIndexItem:
    file: str
    repo: str


class FileIndexLoader:
    @classmethod
    def load(cls, fspath, filesystem):
        items = []
        for file in filesystem.scan(fspath, ".*"):
            cnt = json.loads(filesystem.read_string(path.join(fspath, file)))
            items.append(FileIndexItem(cnt["file"], cnt["repo"]))
        return FileIndex(tuple(items))

    @classmethod
    def save(cls, index, fspath, filesystem):
        for item in index.items:
            filesystem.write_string(
                path.join(fspath, item.repo, hash(item.file)),
                json.dumps({"file": item.file, "repo": item.repo}),
            )
        for removed in index.removed:
            filesystem.delete(path.join(fspath, removed.repo, hash(removed.file)))

    @classmethod
    @contextmanager
    def loaded(cls, fspath, filesystem, save=True):
        index = cls.load(fspath, filesystem)
        yield index
        if save:
            cls.save(index, fspath, filesystem)


class FileIndexError(Exception):
    pass


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
