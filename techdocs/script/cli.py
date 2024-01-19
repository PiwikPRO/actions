import argparse
import os
import sys

from config import ConfigError, ConfigLoader
from copier import Copier, Executor, PrintingExecutor, RelativeFormatter
from detectors import (
    CopyDetector,
    DeleteDetector,
    OperationDetectorChain,
    PlantUMLDiagramsDetector,
    UnnecessaryOperationsFilteringDetector,
)
from filesystem import Filesystem
from index import FileIndexLoader

INDEX_DIRECTORY = ".index"

if __name__ == "__main__":
    fs = Filesystem()
    parser = argparse.ArgumentParser(
        epilog="""A program, that synchronizes files between two directories, using a configuration file."""
    )
    parser.add_argument("command", choices=["copy"])
    parser.add_argument("--index", dest="index", required=True)
    parser.add_argument("--from", dest="from_path", required=True)
    parser.add_argument("--to", dest="to_path", required=True)
    parser.add_argument("--config", dest="config_path", required=True)
    parser.add_argument("--branch", dest="branch", default="master")
    parser.add_argument("--author", dest="author", default="unknown author")
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.command == "copy":
        try:
            with FileIndexLoader.loaded(
                os.path.join(args.to_path, INDEX_DIRECTORY), fs, not args.dry_run
            ) as index:
                config = ConfigLoader.default(args.from_path, args.to_path, fs).load(
                    args.config_path
                )
                Copier(
                    OperationDetectorChain(
                        CopyDetector(
                            args.from_path,
                            args.to_path,
                            args.author,
                            args.branch,
                            config,
                        ),
                        PlantUMLDiagramsDetector(),
                        DeleteDetector(args.index, index, args.from_path, args.to_path),
                        UnnecessaryOperationsFilteringDetector(),
                    ).operations(fs),
                    fs,
                    PrintingExecutor(formatter=RelativeFormatter(args.to_path, args.from_path))
                    if args.dry_run
                    else Executor(fs, formatter=RelativeFormatter(args.to_path, args.from_path)),
                ).execute()
        except ConfigError as e:
            print(f"Config file load error: {e}")
            sys.exit(1)
