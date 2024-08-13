import abc
import json
from dataclasses import dataclass
from os import path
from typing import List

import nodes


class ConfigError(Exception):
    pass


class DocumentError(Exception):
    pass


@dataclass
class ConfigDocumentEntry:
    project: str
    source: str
    destination: str
    exclude: List[str]


@dataclass
class Config:
    documents: List[ConfigDocumentEntry]


# Validators applied to the whole config
class ConfigValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, config: dict):
        pass


class ConfigLoader:
    @classmethod
    def default(cls, from_path, to_path, filesystem) -> "ConfigLoader":
        return cls(
            filesystem,
            [DocumentsKeyMustExist(), DocumentsKeyMustBeList()],
            [
                SourceKeyMustExist(),
                SourceKeyMustBeFileOrContainWildcard(),
                DestinationKeyMustExist(),
                ExcludeIfExistsMustBeList(),
                SourceFileMustExist(from_path, filesystem),
                WildardsInTheMiddleAreApplicableOnlyToDirectories(),
                IfSourceIsDirectoryThenDestinationMustAlsoBeDirectory(),
                ProjectKeyMustExist(),
                ProjectMustExist(ProjectDetailsReader(to_path, filesystem)),
                PathMustNotBeAbsolute("source"),
                PathMustNotBeAbsolute("destination"),
            ],
        )

    def __init__(
        self,
        filesystem,
        config_validators: List[ConfigValidator],
        document_validators: List[ConfigValidator],
    ):
        self.filesystem = filesystem
        self.config_validators = config_validators
        self.document_validators = document_validators

    def load(self, config_path: str, skip_invalid_documents=False) -> Config:
        try:
            config_json = self.filesystem.read_string(config_path)
        except FileNotFoundError:
            raise ConfigError(f"Config file `{config_path}` not found")
        try:
            raw_policy = json.loads(config_json)
        except ValueError:
            raise ConfigError(f"Config file `{config_path}` is not a valid JSON file")
        for validator in self.config_validators:
            validator.validate(raw_policy)
        rules = []
        for document_rule in raw_policy["documents"]:
            try:
                for validator in self.document_validators:
                    validator.validate(document_rule)
                rules.append(
                    ConfigDocumentEntry(
                        document_rule["project"],
                        document_rule["source"],
                        document_rule["destination"],
                        document_rule["exclude"] if "exclude" in document_rule else [],
                    )
                )
            except DocumentError as e:
                if not skip_invalid_documents:
                    raise ConfigError(e)
                print(f"Warning: {e}")
        return Config(rules)


class ProjectKeyMustExist(ConfigValidator):
    def validate(self, config):
        if "project" not in config:
            raise ConfigError(
                f"Each document entry must contain a project name under `project` key. Offending config: {config}"
            )


class DocumentsKeyMustExist(ConfigValidator):
    def validate(self, config):
        if "documents" not in config:
            raise ConfigError(
                f"Config must contain a documents section under `documents` key. Offending config: {config}"
            )


class DocumentsKeyMustBeList(ConfigValidator):
    def validate(self, config):
        if not isinstance(config["documents"], list):
            raise ConfigError(
                f"Config's `documents` key must be a list. Offending config: {config}"
            )


class SourceKeyMustExist(ConfigValidator):
    def validate(self, config):
        if "source" not in config:
            raise ConfigError(
                f"Document rule must contain a source under `source` key. Offending config: {config}"
            )


class SourceKeyMustBeFileOrContainWildcard(ConfigValidator):
    def validate(self, config):
        if (not nodes.looks_fileish(config["source"])) and (not "*" in config["source"]):
            raise ConfigError(
                f"Source: `{config['source']}`  must either contain a wildcard or be a file. Offending config: {config}"
            )


class DestinationKeyMustExist(ConfigValidator):
    def validate(self, config):
        if "destination" not in config:
            raise ConfigError(
                f"Document rule must contain a destination under `destination` key. Offending config: {config}"
            )


class ExcludeIfExistsMustBeList(ConfigValidator):
    def validate(self, config):
        if "exclude" in config and not isinstance(config["exclude"], list):
            raise ConfigError(
                f"Document rule's `exclude` key must be a list. Offending config: {config}"
            )


class PathMustNotBeAbsolute(ConfigValidator):
    def __init__(self, key) -> None:
        self.key = key

    def validate(self, config):
        if path.isabs(config[self.key]):
            raise ConfigError(
                f"Path `{config[self.key]}` must not be absolute. Offending config: {config}"
            )


class ProjectMustExist(ConfigValidator):
    def __init__(self, project_reader) -> None:
        self.reader = project_reader

    def validate(self, config: dict) -> dict:
        try:
            self.reader.doc_path(config["project"])
        except ProjectDoesNotExist:
            raise DocumentError(
                f"Project `{config['project']}` is not declared in target's projects.json. Offending config: {config}"
            )


class SourceFileMustExist(ConfigValidator):
    def __init__(self, from_path, filesystem):
        self.from_path = from_path
        self.filesystem = filesystem

    def validate(self, config):
        if nodes.looks_wildcardish(config["source"]):
            # This validator is not applicable to wildcardish paths
            return
        if nodes.looks_fileish(config["source"]) and not self.filesystem.is_file(
            path.join(self.from_path, config["source"])
        ):
            raise ConfigError(f"Source file `{config['source']}` does not exist")


class IfSourceIsDirectoryThenDestinationMustAlsoBeDirectory(ConfigValidator):
    def validate(self, config):
        if nodes.looks_dirish(config["source"]) and not nodes.looks_dirish(config["destination"]):
            raise ConfigError(
                f"Source is a directory but destination is not. Did you forget to add a trailing slash to desination? "
                f"Offending config: {config}"
            )


class WildardsInTheMiddleAreApplicableOnlyToDirectories(ConfigValidator):
    def validate(self, config):
        if "*" in config["source"][:-1] and not nodes.looks_dirish(config["destination"]):
            raise ConfigError(
                f"Putting wildcards in the middle of the pattern is only supported if the destination is a directory. "
                f"Offending config: {config}"
            )


# Reads the projects.json file and returns the path to the project's docs directory in Tech-docs repository
class ProjectDetailsReader:
    def __init__(self, directory, filesystem):
        self.directory = directory
        self.filesystem = filesystem
        self._projects = None

    def doc_path(self, project):
        if project not in self.projects:
            raise ProjectDoesNotExist(f"Project {project} does not exist")
        return self.projects[project]["path"]

    @property
    def projects(self):
        if not self._projects:
            self._projects = json.loads(
                self.filesystem.read_string(path.join(self.directory, "projects.json"))
            )
        return self._projects


class ProjectDoesNotExist(Exception):
    pass
