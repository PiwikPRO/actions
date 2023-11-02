import abc
from typing import List
from dataclasses import dataclass
import json
from os import path

import nodes


class ConfigError(Exception):
    pass


@dataclass
class ConfigDocumentEntry:
    source: str
    destination: str
    exclude: List[str]


@dataclass
class Config:
    project: str
    documents: ConfigDocumentEntry


# Validators applied to the whole config
class RootValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, config: dict):
        pass


# Validators applied to each entry in the documents section
class EntryValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, project: str, entry_config: dict):
        pass


class ConfigLoader:
    @classmethod
    def default(cls, to_path, filesystem) -> "ConfigLoader":
        return cls(
            filesystem,
            [ProjectKeyMustExist(), DocumentsKeyMustExist(), DocumentsKeyMustBeList()],
            [
                SourceKeyMustExist(),
                SourceKeyMustBeFileOrContainWildcard(),
                DestinationKeyMustExist(),
                ExcludeIfExistsMustBeList(),
                DestinationPathMustBePrefixedWithProjectDocsPath(
                    ProjectDetailsReader(to_path, filesystem)
                ),
            ],
        )

    def __init__(
        self,
        filesystem,
        root_validators: List[RootValidator],
        entry_validators: List[EntryValidator],
    ):
        self.filesystem = filesystem
        self.root_validators = root_validators
        self.entry_validators = entry_validators

    def load(self, config_path: str) -> Config:
        try:
            config_json = self.filesystem.read_string(config_path)
        except FileNotFoundError:
            raise ConfigError(f"Config file `{config_path}` not found")
        try:
            raw_policy = json.loads(config_json)
        except ValueError:
            raise ConfigError(f"Config file `{config_path}` is not a valid JSON file")
        for validator in self.root_validators:
            validator.validate(raw_policy)
        rules = []
        for document_rule in raw_policy["documents"]:
            for validator in self.entry_validators:
                validator.validate(raw_policy["project"], document_rule)
            rules.append(
                ConfigDocumentEntry(
                    document_rule["source"],
                    document_rule["destination"],
                    document_rule["exclude"] if "exclude" in document_rule else [],
                )
            )
        return Config(raw_policy["project"], rules)


class ProjectKeyMustExist(RootValidator):
    def validate(self, config):
        if "project" not in config:
            raise ConfigError("Config must contain a project name under `project` key")


class DocumentsKeyMustExist(RootValidator):
    def validate(self, config):
        if "documents" not in config:
            raise ConfigError(
                "Config must contain a documents section under `documents` key"
            )


class DocumentsKeyMustBeList(RootValidator):
    def validate(self, config):
        if not isinstance(config["documents"], list):
            raise ConfigError("Config's `documents` key must be a list")


class SourceKeyMustExist(EntryValidator):
    def validate(self, project, config):
        if "source" not in config:
            raise ConfigError("Document rule must contain a source under `source` key")


class SourceKeyMustBeFileOrContainWildcard(EntryValidator):
    def validate(self, project, config):
        if (not nodes.looks_fileish(config["source"])) and (
            not "*" in config["source"]
        ):
            raise ConfigError(
                f"Source: `{config['source']}`  must either contain a wildcard or be a file"
            )


class DestinationKeyMustExist(EntryValidator):
    def validate(self, project, config):
        if "destination" not in config:
            raise ConfigError(
                "Document rule must contain a destination under `destination` key"
            )


class ExcludeIfExistsMustBeList(EntryValidator):
    def validate(self, project, config):
        if "exclude" in config and not isinstance(config["exclude"], list):
            raise ConfigError("Document rule's `exclude` key must be a list")


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


class DestinationPathMustBePrefixedWithProjectDocsPath:
    def __init__(self, project_reader: ProjectDetailsReader) -> None:
        self.reader = project_reader

    def validate(self, project, config):
        try:
            if not config["destination"].startswith(self.reader.doc_path(project)):
                raise ConfigError(
                    f"Destination path `{config['destination']}` must be prefixed with project docs path `{self.reader.doc_path(project)}`"
                )
        except KeyError:
            raise ConfigError(
                f"Project `{project}` does not exist in project details file"
            )
        except FileNotFoundError:
            raise ConfigError(
                f"File `projects.json` was not found in the destination directory"
            )
