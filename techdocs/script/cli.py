import argparse
import os
import sys

from config import ConfigError, ConfigLoader
from copier import Copier, Executor, PrintingExecutor
from filesystem import Filesystem
from operations import CopyDetector, DeleteDetector, IndexLoader

if __name__ == "__main__":
    fs = Filesystem()
    parser = argparse.ArgumentParser(
        epilog="""A program, that copies files from one directory to another, based on a configuration file."""
    )
    parser.add_argument("command", choices=["copy"])
    parser.add_argument("--repo", dest="repo", required=True)
    parser.add_argument("--from", dest="from_path", required=True)
    parser.add_argument("--to", dest="to_path", required=True)
    parser.add_argument("--config", dest="config_path", required=True)
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.command == "copy":
        try:
            # zz- prefix to make it the last file in the directory listing for example during PR review
            with IndexLoader.loaded(
                os.path.join(args.to_path, "zz-index"), fs, not args.dry_run
            ) as index:
                Copier(
                    DeleteDetector(
                        args.repo,
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
                    ),
                    fs,
                    PrintingExecutor() if args.dry_run else Executor(fs),
                ).execute(args.from_path)
        except ConfigError as e:
            print(f"Config file load error: {e}")
            sys.exit(1)
