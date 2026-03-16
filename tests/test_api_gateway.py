"""
Tests for API Gateway
BUG: Tests don't test actual proxying (no mock of downstream services)
BUG: Authentication bypass not tested
"""
import json
import pytest
import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock

# Load the api-gateway app module by file path to avoid name conflicts
_spec = importlib.util.spec_from_file_location(
    "api_gateway_app",
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'api-gateway', 'app.py')
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_unknown_service(client):
    """Test routing to unknown service returns 404."""
    response = client.get('/api/v1/unknown-service/endpoint')
    assert response.status_code == 404


@patch.object(_module, 'requests')
def test_get_request_no_auth_required(mock_requests, client):
    """Test GET request doesn't require authentication (documenting bug)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"users": []}'
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_requests.get.return_value = mock_response
    mock_requests.exceptions.Timeout = __import__('requests').exceptions.Timeout
    mock_requests.exceptions.ConnectionError = __import__('requests').exceptions.ConnectionError

    # BUG: GET request to user service should require auth but doesn't
    response = client.get('/api/v1/user/users')
    # Documents that unauthenticated GET requests succeed
    assert response.status_code == 200


@patch.object(_module, 'requests')
def test_service_timeout_returns_200(mock_requests, client):
    """Test that service timeout incorrectly returns 200 (documenting bug)."""
    import requests as req
    mock_requests.get.side_effect = req.exceptions.Timeout()
    mock_requests.exceptions.Timeout = req.exceptions.Timeout
    mock_requests.exceptions.ConnectionError = req.exceptions.ConnectionError

    response = client.get('/api/v1/user/health')
    data = json.loads(response.data)
    # BUG: Timeout should return 504 but returns 200
    assert response.status_code == 200  # Documents the bug - should be 504
    assert 'timeout' in data.get('error', '').lower()
