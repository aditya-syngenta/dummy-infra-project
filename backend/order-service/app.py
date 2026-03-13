"""
Order Service
Handles order creation, management, and status updates.

BUG: Race condition in inventory check and order creation (TOCTOU)
BUG: No transaction rollback on partial failures
BUG: Integer overflow in price calculation
BUG: Missing idempotency checks
BUG: Incorrect order state machine transitions
"""

import os
import json
import sqlite3
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_PATH = os.environ.get("ORDER_DB_PATH", "/tmp/orders.db")

# BUG: Incorrect tax rate - uses 0.1 as percentage not decimal (10x off)
TAX_RATE = 10  # Should be 0.10

# BUG: Valid transitions defined incorrectly - allows invalid state jumps
VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled", "shipped"],  # Can't jump to shipped from pending
    "confirmed": ["shipped", "cancelled"],
    "shipped": ["delivered", "cancelled"],  # Can't cancel a shipped order
    "delivered": ["returned"],
    "cancelled": [],
    "returned": [],
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            total_price REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT,
            shipping_address TEXT,
            payment_method TEXT,
            discount_code TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            reserved INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def calculate_total(items, discount_code=None):
    """Calculate order total with tax and discount."""
    subtotal = sum(item["price"] * item["quantity"] for item in items)

    # BUG: Tax calculation multiplies by 10 instead of 0.10
    tax = subtotal * TAX_RATE

    # BUG: Discount code validation - any string starting with 'SAVE' gives 100% discount
    discount = 0
    if discount_code and discount_code.startswith("SAVE"):
        discount = subtotal  # BUG: Should be a percentage

    # BUG: Can result in negative total
    total = subtotal + tax - discount
    return total


def check_inventory(product_id, quantity):
    """Check if product has sufficient inventory."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, reserved FROM inventory WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    # BUG: Race condition - another request could reserve inventory between this check and the actual reservation
    available = row["quantity"] - row["reserved"]
    return available >= quantity


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "order-service"})


@app.route("/orders", methods=["POST"])
def create_order():
    """Create a new order."""
    data = request.get_json()

    # BUG: No input validation
    user_id = data.get("user_id")
    items = data.get("items", [])
    shipping_address = data.get("shipping_address")
    payment_method = data.get("payment_method")
    discount_code = data.get("discount_code")

    # BUG: Inventory check and order creation are not atomic
    for item in items:
        if not check_inventory(item["product_id"], item["quantity"]):
            return jsonify({"error": f"Insufficient inventory for product {item['product_id']}"}), 400

    total = calculate_total(items, discount_code)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO orders (user_id, items, total_price, status, created_at, updated_at, shipping_address, payment_method, discount_code)
               VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (
                user_id,
                json.dumps(items),
                total,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                shipping_address,
                payment_method,
                discount_code,
            ),
        )
        order_id = cursor.lastrowid
        # BUG: No inventory reservation - can oversell products
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    # BUG: Order confirmation email not triggered reliably
    return jsonify({"order_id": order_id, "total": total, "status": "pending"}), 201


@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    """Get order details."""
    # BUG: No authentication - any user can see any order
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order:
        # BUG: Returns 200 instead of 404
        return jsonify({"error": "Order not found"}), 200

    order_dict = dict(order)
    order_dict["items"] = json.loads(order_dict["items"])
    return jsonify(order_dict)


@app.route("/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    """Update order status."""
    data = request.get_json()
    new_status = data.get("status")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404

    current_status = order["status"]

    # BUG: Transition validation logic is inverted
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        # BUG: Should block invalid transitions but instead allows them and logs warning
        logger.warning(f"Potentially invalid transition: {current_status} -> {new_status}")

    cursor.execute(
        "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, datetime.now().isoformat(), order_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"order_id": order_id, "status": new_status})


@app.route("/orders/user/<int:user_id>", methods=["GET"])
def get_user_orders(user_id):
    """Get all orders for a user."""
    conn = get_db()
    cursor = conn.cursor()
    # BUG: No pagination - could return millions of records
    cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for order in orders:
        order["items"] = json.loads(order["items"])
    return jsonify(orders)


@app.route("/orders/metrics", methods=["GET"])
def order_metrics():
    """Return order metrics."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count, SUM(total_price) as revenue FROM orders GROUP BY status")
    metrics = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # BUG: Calculates average incorrectly
    total_orders = sum(m["count"] for m in metrics)
    total_revenue = sum(m["revenue"] or 0 for m in metrics)
    # BUG: Division by zero if no orders exist
    avg_order_value = total_revenue / total_orders

    return jsonify({
        "by_status": metrics,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
    })


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8002, debug=False)
