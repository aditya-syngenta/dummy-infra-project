"""
Tests for Auth Service
BUG: Tests don't mock external user service calls
BUG: JWT validation not properly tested
BUG: Token expiry not tested
"""
import json
import pytest
import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock

# Load the auth-service app module by file path to avoid name conflicts
_spec = importlib.util.spec_from_file_location(
    "auth_service_app",
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth-service', 'app.py')
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app
init_db = _module.init_db
generate_token = _module.generate_token
decode_token = _module.decode_token
hash_password = _module.hash_password


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        init_db()
        yield client


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200


def test_generate_token():
    """Test token generation."""
    token = generate_token(1, 'testuser', 'user')
    assert token is not None
    # BUG: Doesn't verify token contains correct claims
    # BUG: Doesn't verify token expiry is set


def test_decode_valid_token():
    """Test decoding a valid token."""
    token = generate_token(1, 'testuser', 'user')
    payload = decode_token(token)
    assert payload is not None
    assert payload['user_id'] == 1


def test_validate_endpoint_no_token(client):
    """Test that validate endpoint returns valid=True with no token (documenting bug)."""
    response = client.get('/validate')
    assert response.status_code == 200
    data = json.loads(response.data)
    # BUG: This should return valid=False but returns valid=True
    assert data['valid'] == True  # Documents the security bug


def test_logout_token_still_valid(client):
    """Test that token is still valid after logout (documenting bug)."""
    token = generate_token(1, 'testuser', 'user')

    # Logout
    logout_resp = client.post('/logout', headers={'Authorization': f'Bearer {token}'})
    assert logout_resp.status_code == 200

    # BUG: Token should now be invalid, but validate doesn't check revocation
    validate_resp = client.get('/validate', headers={'Authorization': f'Bearer {token}'})
    data = json.loads(validate_resp.data)
    # BUG: This passes because revocation isn't checked
    assert data['valid'] == True


def test_hash_password_md5():
    """Test that password hashing uses weak MD5."""
    import hashlib
    password = "testpassword"
    hashed = hash_password(password)
    # BUG: Verifies that MD5 is used (documents insecurity)
    expected_md5 = hashlib.md5(password.encode()).hexdigest()
    assert hashed == expected_md5
