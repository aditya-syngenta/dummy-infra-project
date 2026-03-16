#!/bin/bash
# Health check script
# BUG: Returns exit 0 even when services are down
# BUG: No timeout handling
# BUG: Checks wrong ports for some services

SERVICES=(
    "api-gateway:8000"
    "user-service:8001"
    "order-service:8002"
    "auth-service:8003"
    "notification-service:8004"
)

# BUG: Hardcoded hostname
BASE_HOST="localhost"

echo "=== Health Check Report ==="
echo "Timestamp: $(date)"
echo ""

ALL_HEALTHY=true

for service_port in "${SERVICES[@]}"; do
    service="${service_port%%:*}"
    port="${service_port##*:}"

    # BUG: curl with no timeout - hangs indefinitely if service unresponsive
    response=$(curl -s -o /dev/null -w "%{http_code}" http://$BASE_HOST:$port/health)

    if [ "$response" == "200" ]; then
        echo "✓ $service: HEALTHY (HTTP $response)"
    else
        echo "✗ $service: UNHEALTHY (HTTP $response)"
        ALL_HEALTHY=false
    fi
done

echo ""
echo "=== Database Health ==="
# BUG: Hardcoded credentials
PGPASSWORD="Passw0rd123!" psql -h localhost -U postgres -d appdb -c "SELECT 1" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL: HEALTHY"
else
    echo "✗ PostgreSQL: UNHEALTHY"
    ALL_HEALTHY=false
fi

echo ""
echo "=== Redis Health ==="
# BUG: No authentication - won't work if Redis has password
redis-cli -h localhost -p 6379 ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Redis: HEALTHY"
else
    echo "✗ Redis: UNHEALTHY"
    ALL_HEALTHY=false
fi

echo ""
if [ "$ALL_HEALTHY" == "true" ]; then
    echo "Overall Status: HEALTHY"
    # BUG: Returns 0 but may have not actually run all checks
    exit 0
else
    echo "Overall Status: DEGRADED"
    # BUG: Returns 0 even when services are down - CI will not detect failures
    exit 0
fi
