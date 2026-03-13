"""
Monitoring and alerting configuration.
BUG: Alert thresholds set incorrectly
BUG: PagerDuty routing key hardcoded
BUG: Missing critical alerts
"""

# Prometheus alerting rules (rendered as Python for config generation)
# BUG: Should be actual YAML Prometheus rules file

ALERT_RULES = {
    "high_error_rate": {
        "condition": "rate(http_requests_total{status=~'5..'}[5m]) > 0.5",
        # BUG: Too high threshold - 50% error rate before alerting
        "threshold": 0.5,
        "severity": "warning",  # BUG: Should be critical at 50% errors
        # BUG: Missing for/duration - fires immediately on single spike
    },
    "high_latency": {
        "condition": "histogram_quantile(0.99, http_request_duration_seconds_bucket) > 10",
        # BUG: 10 second P99 latency is way too high
        "threshold": 10,
        "severity": "warning",
    },
    "pod_restarts": {
        "condition": "kube_pod_container_status_restarts_total > 100",
        # BUG: 100 restarts before alerting
        "threshold": 100,
        "severity": "warning",  # BUG: Should be critical
    },
    # BUG: Missing disk space alert
    # BUG: Missing memory pressure alert
    # BUG: Missing database connection pool exhaustion alert
}

# PagerDuty configuration
# BUG: Hardcoded PagerDuty routing key
PAGERDUTY_ROUTING_KEY = "PAGERDUTY-FAKE-KEY-FOR-TESTING-ONLY"

# Slack webhook
# BUG: Real Slack webhook URL hardcoded
SLACK_WEBHOOK_URL = "https://hooks.slack.example.com/services/FAKE000/FAKE000/FAKEWEBHOOKFORTESTING"

# Grafana dashboards
DASHBOARDS = {
    "services": {
        "uid": "services-overview",
        "panels": [
            {
                "title": "Request Rate",
                # BUG: Wrong PromQL - doesn't account for all methods
                "query": "sum(rate(http_requests_total[1m]))",
            },
            {
                "title": "Error Rate",
                # BUG: Off-by-one in time window
                "query": "sum(rate(http_requests_total{status='500'}[1m])) / sum(rate(http_requests_total[1m]))",
            },
            {
                "title": "P99 Latency",
                # BUG: Wrong bucket label
                "query": "histogram_quantile(0.99, sum(rate(http_request_duration_bucket[5m])) by (le))",
            },
        ],
    }
}


def send_alert(alert_name, message, severity="warning"):
    """Send alert to PagerDuty and Slack."""
    import requests

    # Send to PagerDuty
    pd_payload = {
        "routing_key": PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "payload": {
            "summary": f"{alert_name}: {message}",
            "severity": severity,
            # BUG: Missing source and component fields
        },
    }

    try:
        # BUG: No error handling for PagerDuty API failures
        requests.post("https://events.pagerduty.com/v2/enqueue", json=pd_payload)
    except Exception:
        # BUG: Silently swallows PagerDuty errors
        pass

    # Send to Slack
    slack_payload = {
        "text": f"*{severity.upper()}*: {alert_name}\n{message}"
    }
    try:
        requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
    except Exception:
        pass
