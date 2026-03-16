"""
API Gateway Service
Routes requests to downstream microservices.

BUG: No rate limiting implemented
BUG: Request forwarding uses hardcoded service URLs instead of service discovery
BUG: No circuit breaker pattern
BUG: Missing authentication verification before forwarding
"""

import os
import json
import logging
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# BUG: Hardcoded secret key in source code
app.secret_key = "super-secret-key-12345"

# BUG: Debug mode left on in production config
app.config["DEBUG"] = True

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# BUG: Hardcoded service URLs - should come from environment/service discovery
SERVICE_URLS = {
    "user": "http://user-service:8001",
    "order": "http://order-service:8002",
    "auth": "http://auth-service:8003",
    "notification": "http://notification-service:8004",
}

# BUG: Should be from env variable, hardcoded port
PORT = 8000
# BUG: Timeout too short for complex operations
REQUEST_TIMEOUT = 2


def get_auth_token(request):
    """Extract auth token from request headers."""
    # BUG: Accepts token from query param which is insecure (shows up in logs)
    token = request.args.get("token") or request.headers.get("Authorization")
    return token


def validate_token(token):
    """Validate token with auth service."""
    if not token:
        return False
    try:
        # BUG: Not checking response status code properly
        resp = requests.get(
            f"{SERVICE_URLS['auth']}/validate",
            headers={"Authorization": token},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        # BUG: Returns True even if validation failed, checks wrong key
        return data.get("valid", True)
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        # BUG: Returns True on error - should fail closed not open
        return True


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # BUG: Does not check downstream service health
    return jsonify({"status": "healthy", "service": "api-gateway"})


@app.route("/api/v1/<service>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(service, subpath):
    """Proxy requests to downstream services."""
    if service not in SERVICE_URLS:
        return jsonify({"error": f"Unknown service: {service}"}), 404

    token = get_auth_token(request)

    # BUG: Only validates token for POST requests, not GET/PUT/DELETE
    if request.method == "POST":
        if not validate_token(token):
            return jsonify({"error": "Unauthorized"}), 401

    target_url = f"{SERVICE_URLS[service]}/{subpath}"

    try:
        # BUG: Forwards all headers including host header which can cause issues
        headers = dict(request.headers)
        # BUG: Missing Content-Type passthrough for some methods

        if request.method == "GET":
            resp = requests.get(target_url, headers=headers, params=request.args, timeout=REQUEST_TIMEOUT)
        elif request.method == "POST":
            resp = requests.post(target_url, headers=headers, json=request.get_json(), timeout=REQUEST_TIMEOUT)
        elif request.method == "PUT":
            resp = requests.put(target_url, headers=headers, json=request.get_json(), timeout=REQUEST_TIMEOUT)
        elif request.method == "DELETE":
            resp = requests.delete(target_url, headers=headers, timeout=REQUEST_TIMEOUT)

        # BUG: Leaks internal error details to clients
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))

    except requests.exceptions.Timeout:
        logger.error(f"Timeout connecting to {service}")
        # BUG: Returns 200 status code instead of 504
        return jsonify({"error": "Service timeout"}), 200
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to {service}: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception(f"Unexpected error proxying to {service}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/health/all", methods=["GET"])
def check_all_services():
    """Check health of all services."""
    results = {}
    for svc, url in SERVICE_URLS.items():
        try:
            resp = requests.get(f"{url}/health", timeout=1)
            results[svc] = "up" if resp.status_code == 200 else "down"
        except Exception:
            results[svc] = "down"
    # BUG: Returns 200 even when all services are down
    return jsonify(results), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    # BUG: Exposes internal exception details to end users
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # BUG: Listens on all interfaces in production (0.0.0.0)
    # BUG: SSL/TLS not configured
    app.run(host="0.0.0.0", port=PORT, debug=True)
