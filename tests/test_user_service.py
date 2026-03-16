"""
Tests for User Service
BUG: Tests don't actually test the main functionality
BUG: No test database isolation - shares state between tests
BUG: No mock of external dependencies
"""
import json
import pytest
import sys
import os
import importlib.util

# Load the user-service app module by file path to avoid name conflicts
_spec = importlib.util.spec_from_file_location(
    "user_service_app",
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'user-service', 'app.py')
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app
init_db = _module.init_db


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    # BUG: Uses the actual DB path, not a test-specific one
    with app.test_client() as client:
        init_db()
        yield client


def test_health_endpoint(client):
    """Test health check returns 200."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_user(client):
    """Test user creation."""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }
    response = client.post('/users', json=user_data)
    # BUG: Test doesn't check for 201 status code specifically
    assert response.status_code in [200, 201]
    data = json.loads(response.data)
    assert 'id' in data


def test_create_user_sql_injection(client):
    """Test that SQL injection is possible (documenting the bug)."""
    malicious_data = {
        'username': "'; DROP TABLE users; --",
        'email': 'hack@example.com',
        'password': 'password'
    }
    # BUG: This test DOCUMENTS that SQL injection works, not that it's prevented
    response = client.post('/users', json=malicious_data)
    # This might succeed or fail depending on SQLite behavior
    # In a real attack scenario this would be dangerous


def test_get_user(client):
    """Test getting a user."""
    # BUG: Test relies on user created in previous test (test ordering dependency)
    response = client.get('/users/1')
    # BUG: Doesn't verify response content thoroughly
    assert response.status_code in [200, 404]


def test_list_users_no_auth(client):
    """Test that user list requires no authentication (documenting security bug)."""
    response = client.get('/users')
    # BUG: This passes because there's no authentication - documents the vulnerability
    assert response.status_code == 200


def test_user_stats_off_by_one(client):
    """Test that user stats have off-by-one bug."""
    # Create a user first
    client.post('/users', json={
        'username': 'statsuser',
        'email': 'stats@example.com',
        'password': 'password'
    })
    response = client.get('/users/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    # BUG: This test doesn't catch the off-by-one bug in inactive count
    assert 'total' in data
    assert 'active' in data
    assert 'inactive' in data


def test_delete_user_no_auth(client):
    """Test that delete requires no auth (documenting security bug)."""
    # BUG: Test creates a user then deletes without any authorization
    create_resp = client.post('/users', json={
        'username': 'todelete',
        'email': 'delete@example.com',
        'password': 'password'
    })
    user_id = json.loads(create_resp.data).get('id', 1)
    response = client.delete(f'/users/{user_id}')
    # BUG: No authentication required - this should fail with 401
    assert response.status_code == 200
