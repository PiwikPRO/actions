import argparse

import report_processor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        epilog="""K6 benchmark and reporting automation"""
    )

    parser.add_argument("--reports_path", default="reports")
    parser.add_argument("--benchmark_path", default="benchmark")
    args = parser.parse_args()

    report_processor.process(args.reports_path, args.benchmark_path)
