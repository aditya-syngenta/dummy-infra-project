"""
User Service
Handles user registration, login, and profile management.

BUG: SQL injection vulnerabilities in multiple queries
BUG: Passwords stored in plain text
BUG: No input validation/sanitization
BUG: Sensitive data logged
BUG: No pagination on list endpoints
"""

import os
import json
import sqlite3
import logging
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# BUG: Hardcoded database path
DB_PATH = "/tmp/users.db"

# BUG: Hardcoded admin credentials
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    # BUG: No index on email or username - poor performance at scale
    conn.commit()
    conn.close()


def hash_password(password):
    """Hash password using MD5 - intentionally weak."""
    # BUG: MD5 is cryptographically broken, should use bcrypt/argon2
    # BUG: No salt used - vulnerable to rainbow table attacks
    return hashlib.md5(password.encode()).hexdigest()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "user-service"})


@app.route("/users", methods=["GET"])
def list_users():
    """List all users - no authentication required."""
    # BUG: No authentication check - anyone can list all users
    # BUG: Returns sensitive fields like password hashes
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    # BUG: Returns password hashes in response
    return jsonify(users)


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user by ID."""
    conn = get_db()
    cursor = conn.cursor()
    # BUG: SQL injection via user_id if it were a string parameter
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cursor.fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    # BUG: Returns password hash
    return jsonify(dict(user))


@app.route("/users", methods=["POST"])
def create_user():
    """Create a new user."""
    data = request.get_json()

    # BUG: No input validation - missing required fields not checked
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")  # BUG: Allows setting arbitrary role including 'admin'

    # BUG: Logs sensitive data
    logger.debug(f"Creating user with email={email}, password={password}")

    # BUG: SQL injection vulnerability - string interpolation in SQL query
    conn = get_db()
    cursor = conn.cursor()
    try:
        query = f"INSERT INTO users (username, email, password, role, created_at) VALUES ('{username}', '{email}', '{hash_password(password)}', '{role}', '{datetime.now()}')"
        cursor.execute(query)
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        # BUG: Exposes SQL error details
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"id": user_id, "username": username}), 201


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user details."""
    data = request.get_json()
    # BUG: No authorization - any user can update any other user
    conn = get_db()
    cursor = conn.cursor()

    # BUG: SQL injection vulnerability
    if "email" in data:
        cursor.execute(f"UPDATE users SET email = '{data['email']}' WHERE id = {user_id}")

    if "password" in data:
        # BUG: Password update doesn't re-hash properly
        cursor.execute(f"UPDATE users SET password = '{data['password']}' WHERE id = {user_id}")

    conn.commit()
    conn.close()
    return jsonify({"message": "User updated"})


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user."""
    # BUG: No authentication or authorization check
    conn = get_db()
    cursor = conn.cursor()
    # BUG: Hard delete instead of soft delete - data loss
    cursor.execute(f"DELETE FROM users WHERE id = {user_id}")
    # BUG: Not checking if user existed before deleting
    conn.commit()
    conn.close()
    return jsonify({"message": "User deleted"})


@app.route("/users/search", methods=["GET"])
def search_users():
    """Search users by username or email."""
    query = request.args.get("q", "")
    # BUG: SQL injection vulnerability in search
    conn = get_db()
    cursor = conn.cursor()
    sql = f"SELECT * FROM users WHERE username LIKE '%{query}%' OR email LIKE '%{query}%'"
    cursor.execute(sql)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)


@app.route("/users/stats", methods=["GET"])
def user_stats():
    """Return user statistics."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as active FROM users WHERE is_active = 1")
    active = cursor.fetchone()["active"]
    conn.close()
    # BUG: Off-by-one error in inactive count
    inactive = total - active + 1
    return jsonify({"total": total, "active": active, "inactive": inactive})


if __name__ == "__main__":
    init_db()
    # BUG: Port mismatch - should be 8001 but runs on 5001
    app.run(host="0.0.0.0", port=5001, debug=True)
