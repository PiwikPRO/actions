import sys
import argparse

from copier import Copier, Executor, PrintingExecutor
from config import ConfigLoader, ConfigError
from filesystem import Filesystem
from operations import Detector


if __name__ == "__main__":
    fs = Filesystem()
    parser = argparse.ArgumentParser(
        epilog="""A program, that copies files from one directory to another, based on a configuration file."""
    )
    parser.add_argument("command", choices=["copy"])
    parser.add_argument("--from", dest="from_path", required=True)
    parser.add_argument("--to", dest="to_path", required=True)
    parser.add_argument("--config", dest="config_path", required=True)
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.command == "copy":
        try:
            Copier(
                Detector(
                    args.from_path, args.to_path, ConfigLoader.default(args.to_path, fs).load(
                        args.config_path
                    )
                ),
                fs,
                PrintingExecutor() if args.dry_run else Executor(fs),
            ).execute(
                args.from_path
            )
        except ConfigError as e:
            print(f"Config file load error: {e}")
            sys.exit(1)
