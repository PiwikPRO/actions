import argparse

import report_processor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        epilog="""K6 benchmark and reporting automation"""
    )

    parser.add_argument("--reports_path", default="reports")
    parser.add_argument("--benchmark_path", default="benchmark")
    parser.add_argument("--summary_file", default="summary.json")
    args = parser.parse_args()

    report_processor.process(args.reports_path, args.benchmark_path, args.summary_file)
