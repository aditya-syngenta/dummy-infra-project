"""
Tests for Order Service
BUG: Tests incomplete - most critical paths not tested
BUG: No test for race conditions
BUG: Tax calculation bug not caught by tests
"""
import json
import pytest
import sys
import os
import importlib.util

# Load the order-service app module by file path to avoid name conflicts
_spec = importlib.util.spec_from_file_location(
    "order_service_app",
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'order-service', 'app.py')
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app
init_db = _module.init_db
calculate_total = _module.calculate_total


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        init_db()
        # Seed inventory so order creation doesn't fail with 400
        import sqlite3
        conn = sqlite3.connect(_module.DB_PATH)
        conn.execute("INSERT OR IGNORE INTO inventory (product_id, quantity) VALUES (1, 100)")
        conn.commit()
        conn.close()
        yield client


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200


def test_calculate_total_basic():
    """Test basic total calculation."""
    items = [{'product_id': 1, 'price': 10.0, 'quantity': 2}]
    total = calculate_total(items)
    # BUG: Expected value calculated with buggy TAX_RATE=10 (1000% tax!)
    # Correct would be: 20 * 1.1 = 22.0
    # Buggy code gives: 20 + (20 * 10) = 220.0
    # This test FAILS to catch the bug because it uses the buggy result as expected value
    assert total == 220.0  # BUG: Wrong expected value - should be 22.0


def test_calculate_total_with_discount():
    """Test total with SAVE discount code."""
    items = [{'product_id': 1, 'price': 100.0, 'quantity': 1}]
    # BUG: SAVE discount gives 100% off - completely free order
    total = calculate_total(items, discount_code="SAVE50")
    # BUG: Test doesn't verify this is a bug (free order)
    assert total == 1000.0  # subtotal=100, tax=100*10=1000, discount=100, total=1000


def test_create_order(client):
    """Test order creation."""
    order_data = {
        'user_id': 1,
        'items': [
            {'product_id': 1, 'price': 10.0, 'quantity': 1}
        ],
        'shipping_address': '123 Test St',
        'payment_method': 'credit_card'
    }
    response = client.post('/orders', json=order_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'order_id' in data


def test_get_order_not_found(client):
    """Test getting non-existent order."""
    response = client.get('/orders/99999')
    # BUG: This test expects 200 because of the bug (returns 200 for not found)
    assert response.status_code == 200  # Should be 404


def test_update_order_status_invalid_transition(client):
    """Test invalid status transition is allowed (documenting bug)."""
    # Create an order
    create_resp = client.post('/orders', json={
        'user_id': 1,
        'items': [{'product_id': 1, 'price': 10.0, 'quantity': 1}],
        'shipping_address': '123 Test St',
        'payment_method': 'credit_card'
    })
    order_id = json.loads(create_resp.data).get('order_id')

    # BUG: This invalid transition (pending -> delivered) should be rejected
    # but the bug allows it
    response = client.put(f'/orders/{order_id}/status', json={'status': 'delivered'})
    assert response.status_code == 200  # BUG: Should return 422 for invalid transition
