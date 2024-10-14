from datetime import datetime
import json
import os
import statistics
import sys

ROUND_PRECISION = 3

GREEN_DOT = "\U0001F7E2"
RED_DOT = "\U0001F534"
ARROW_UP = "\U00002197"
ARROW_DOWN = "\U00002198"
ARROW_EQ = "\U00002194"

def process(reports_dir, benchmark_dir, summary_file):
    print("**Automated k6 Benchmark Report**")
    print("--------------------------------")
    report_list = sorted([
        report for report in os.listdir(reports_dir) if os.path.isfile(get_report_uri(reports_dir, report, summary_file))
    ], reverse=True)

    if len(report_list) == 0:
        # Print error messages to stdout so it can be captured and displayed in PR comment if needed
        print("Can't compile the summary - there are no reports to compare with. " +
                        "Tag you default branch first and wait for the base report to be ready. " +
                        "Then we will have something to compare your current benchmark with.")
        sys.exit(0)

    last_report = json.load(open(benchmark_dir + "/" + summary_file))["data"]

    compare_with_reports = []
    report_timestamps = []
    for i in report_list[0:5]:
        old_report = json.load(open(get_report_uri(reports_dir, i, summary_file)))
        compare_with_reports.append(old_report["data"])
        report_timestamps.append(old_report["run"]["end_s_since_epoch"])

    calculate_avg_metrics(last_report, compare_with_reports)

    print_results(last_report, len(compare_with_reports), min(report_timestamps), max(report_timestamps), summary_file)

def print_results(last_report, previous_runs, first_ts, last_ts, summary_file):
    first_ts = str(datetime.fromtimestamp(first_ts))
    last_ts = str(datetime.fromtimestamp(last_ts))
    previous_runs = str(previous_runs)

    if previous_runs == 1:
        print(f"{summary_file}: compared (left value) to the last run, recorded on {first_ts}")
    else:
        print(f"{summary_file}: compared (left value) to the average calculated from the {previous_runs} latest runs. " +
              f"First was recorded on {first_ts} and the last was recorded on {last_ts}.")

    for i in last_report:
        avg = round(last_report[i]["avg"], ROUND_PRECISION)
        val = round(last_report[i]["value"], ROUND_PRECISION)
        cmp_logic = last_report[i]["comparison"]
        description = last_report[i]["description"]
        result = compare(val, avg, cmp_logic)

        print(f"{result['dot']} {description}: {avg} {result['arrow']} {val}")

def get_report_uri(base_dir, report_dir, summary_file):
    return base_dir + "/" + report_dir + "/" + summary_file

def calculate_avg_metrics(last_report, compare_with_reports):
    for i in last_report:
        try:
            last_report[i]["avg"] = statistics.mean(
                [metric[i]["value"] for metric in compare_with_reports]
            )
        except statistics.StatisticsError:
            last_report[i]["avg"] = last_report[i]["value"]

def compare(x, y, logic):

    match cmp(x, y):
        case 1:
            arrow = ARROW_UP
        case -1:
            arrow = ARROW_DOWN
        case _:
            arrow = ARROW_EQ

    match cmp(x, y) * compare_logic_from_str(logic):
        case 1:
            dot = GREEN_DOT
        case -1:
            dot = RED_DOT
        case _:
            dot = GREEN_DOT

    return {"dot": dot, "arrow": arrow}

def compare_logic_from_str(logic_name):
    if logic_name == "higher_is_better":
        logic = 1
    elif logic_name == "lower_is_better":
        logic = -1
    else:
        raise Exception("Unhandled comparison logic: " + logic_name)

    return logic

def cmp(x, y):
    return (x > y) - (x < y)
