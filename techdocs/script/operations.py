import re
from os import path
from dataclasses import dataclass

from config import Config
import nodes


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


class Detector:
    def __init__(
        self, from_path: str, to_path: str, config: Config
    ) -> (
        None
    ):
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

    def for_file(self, path: str):
        for rule in self.copy_rules:
            if rule.match(path):
                return self._create_operation(path, rule)
        return None

    def _create_operation(self, file, rule):
        if nodes.looks_fileish(rule.config.source) and nodes.looks_dirish(rule.config.destination):
            relative_src, relative_dst = (
                file,
                path.join(rule.config.destination, path.basename(file))
            )
        elif nodes.looks_fileish(rule.config.source) and nodes.looks_fileish(rule.config.destination):
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
