import argparse
import os
import sys

from config import ConfigError, ConfigLoader
from copier import Copier, Executor, PrintingExecutor
from filesystem import Filesystem
from operations import (
    CopyDetector,
    DeleteDetector,
    FileIndexLoader,
    UnnecessaryOperationsFilteringDetector,
)

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
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.command == "copy":
        try:
            with FileIndexLoader.loaded(
                os.path.join(args.to_path, INDEX_DIRECTORY), fs, not args.dry_run
            ) as index:
                Copier(
                    UnnecessaryOperationsFilteringDetector(
                        DeleteDetector(
                            args.index,
                            index,
                            args.from_path,
                            args.to_path,
                            CopyDetector(
                                args.from_path,
                                args.to_path,
                                ConfigLoader.default(args.from_path, args.to_path, fs).load(
                                    args.config_path
                                ),
                            ),
                        )
                    ),
                    fs,
                    PrintingExecutor() if args.dry_run else Executor(fs),
                ).execute(args.from_path)
        except ConfigError as e:
            print(f"Config file load error: {e}")
            sys.exit(1)
