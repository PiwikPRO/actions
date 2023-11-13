import os
import sys


class Copier:
    def __init__(self, detector, filesystem, executor=None) -> None:
        self.filesystem = filesystem
        self.detector = detector
        self.executor = executor or Executor(filesystem)

    def execute(self):
        operations = self.detector.detect(self.filesystem)
        if len(operations) == 0:
            print("Nothing to do", file=sys.stderr)
            return
        for operation in operations:
            self.executor.execute(operation)


class Executor:
    def __init__(self, filesystem):
        self.filesystem = filesystem

    def execute(self, operation):
        print(operation)
        if operation.type == operation.TYPE_COPY:
            self.filesystem.copy(operation.source_abs, operation.destination_abs)
        elif operation.type == operation.TYPE_DELETE:
            self.filesystem.delete(operation.source_abs)


class PrintingExecutor:
    def __init__(self, formatter=None) -> None:
        self.formatter = formatter or SimpleFormatter()

    def execute(self, operation):
        print(self.formatter.format(operation))


class SimpleFormatter:
    def format(self, operation):
        return str(operation)


class RelativeMarkdownListFormatter:
    def __init__(self, from_root, to_root) -> None:
        self.from_root = from_root
        self.to_root = to_root

    def format(self, operation):
        if operation.type == operation.TYPE_DELETE:
            return f"* [DELETE] {os.path.relpath(operation.destination_abs, self.to_root)}"
        elif operation.type == operation.TYPE_COPY:
            return f"* [COPY] {os.path.relpath(operation.source_abs, self.from_root)} -> {os.path.relpath(operation.destination_abs, self.to_root)}"

        return ""
