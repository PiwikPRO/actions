import argparse

import report_processor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        epilog="""K6 benchmark and reporting automation"""
    )

    parser.add_argument("--path", default="./reports")
    args = parser.parse_args()

    report_processor.process(args.path)
