import json
import os
import statistics

REPORT_FILE_NAME = "summary.json"

ROUND_PRECISION = 3

GREEN_DOT = "\U0001F7E2"
RED_DOT = "\U0001F534"
ARROW_UP = "\U00002197"
ARROW_DOWN = "\U00002198"
ARROW_EQ = "\U00002194"


def process(dir):
    print("**Automated k6 Benchmark Report**")
    print("--------------------------------")
    report_list = sorted([
        report for report in os.listdir(dir) if os.path.isfile(get_report_uri(dir, report))
    ], reverse=True)

    last_report = json.load(open(get_report_uri(dir, report_list.pop(0))))["data"]

    compare_with_reports = []
    for i in report_list[0:5]:
        old_report = json.load(open(get_report_uri(dir, i)))
        compare_with_reports.append(old_report["data"])

    calculate_avg_metrics(last_report, compare_with_reports)

    print_results(last_report, len(compare_with_reports))


def print_results(last_report, previous_runs):
    print("Compared to average of " + str(previous_runs) + " latest runs")

    for i in last_report:
        avg = round(last_report[i]["avg"], ROUND_PRECISION)
        val = round(last_report[i]["value"], ROUND_PRECISION)
        cmp_logic = last_report[i]["comparison"]
        description = last_report[i]["description"]
        result = compare(val, avg, cmp_logic)

        print(f"{result['dot']} {description}: {avg} {result['arrow']} {val}")


def get_report_uri(base_dir, report_dir):
    return base_dir + "/" + report_dir + "/" + REPORT_FILE_NAME


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
        raise Exception("Unhandled coparison logic: " + logic_name)

    return logic


def cmp(x, y):
    return (x > y) - (x < y)
