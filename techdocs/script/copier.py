import os
import sys
from pathlib import Path


class Copier:
    def __init__(self, operations, filesystem, executor=None) -> None:
        self.filesystem = filesystem
        self.operations = operations
        self.executor = executor or Executor(filesystem)

    def execute(self):
        operations = self.operations
        if len(operations) == 0:
            print("Nothing to do", file=sys.stderr)
            return
        for operation in operations:
            self.executor.execute(operation)


class Executor:
    def __init__(self, filesystem, formatter=None):
        self.formatter = formatter or SimpleFormatter()
        self.filesystem = filesystem

    def execute(self, operation):
        print(operation.mkd(self.formatter))
        operation.execute(self.filesystem)


class PrintingExecutor:
    def __init__(self, formatter=None):
        self.formatter = formatter or SimpleFormatter()

    def execute(self, operation):
        print(operation.mkd(self.formatter))


class SimpleFormatter:
    def format(self, path):
        return str(path)


def is_subpath(path, potential_subpath):
    path = Path(path).resolve()
    potential_subpath = Path(potential_subpath).resolve()
    return potential_subpath in path.parents


class RelativeFormatter:
    def __init__(self, *possible_parents):
        self.parents = possible_parents

    def format(self, path):
        for parent in self.parents:
            if is_subpath(path, parent):
                return str(os.path.relpath(path, parent))
        return str(path)
