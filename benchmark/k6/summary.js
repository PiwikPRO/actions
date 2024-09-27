
export function handleSummary(data) {
    const nowMs = Date.now();
    var summaryObj = {
      "version": "v1",
      "run": {
          "start_s_since_epoch": Math.floor((nowMs - data.state.testRunDurationMs) / 1000),
          "end_s_since_epoch": Math.floor(nowMs / 1000),
      },
      "data": {
        "latency_ms_p50": {
          "value": data.metrics.http_req_duration.values.med,
          "description": "50th percentile latency in milliseconds",
          "comparison": "lower_is_better"
        },
        "latency_ms_p90":{
          "value": data.metrics.http_req_duration.values["p(90)"],
          "description": "90th percentile latency in milliseconds",
          "comparison": "lower_is_better"
        },
        "latency_ms_p95": {
          "value": data.metrics.http_req_duration.values["p(95)"],
          "description": "95th percentile latency in milliseconds",
          "comparison": "lower_is_better"
        },
        "reqps_avg": {
          "value": data.metrics.http_reqs.values.rate,
          "description": "Average number of requests per second",
          "comparison": "higher_is_better"
        },
        "req_failure_rate": {
          "value": data.metrics.http_req_failed.values.rate,
          "description": "The ratio of requests that failed (0-1)",
          "comparison": "lower_is_better"
        },
      }
    };
    try{
      const extraMetrics = getExtraMetrics(data)
      summaryObj.data = Object.assign({}, summaryObj.data, extraMetrics.data)
    } catch(e){
      console.log("Did not collect extra metrics: " + e)
    }
    return {
      [SUMMARY_FILE]: JSON.stringify(summaryObj, null, 2)
    };
  }