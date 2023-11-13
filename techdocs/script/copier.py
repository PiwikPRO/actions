class Copier:
    def __init__(self, detector, filesystem, executor=None) -> None:
        self.filesystem = filesystem
        self.detector = detector
        self.executor = executor or Executor(filesystem)

    def execute(self):
        operations = self.detector.detect(self.filesystem)
        if len(operations) == 0:
            print("Nothing to do")
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
    def execute(self, operation):
        print(operation)
