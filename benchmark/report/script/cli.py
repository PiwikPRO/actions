import argparse

import report_processor

INDEX_DIRECTORY = ".index"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        epilog="""A program, that synchronizes files between two directories, using a configuration file."""
    )

    parser.add_argument("--path", default="./reports")
    args = parser.parse_args()

    report_processor.process(args.path)
