"""
Auth Service
Handles authentication and authorization.

BUG: JWT secret hardcoded
BUG: Tokens never expire
BUG: No refresh token rotation
BUG: Weak JWT algorithm (HS256 instead of RS256)
BUG: Brute force protection missing
BUG: Session fixation vulnerability
"""

import os
import json
import time
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# BUG: Using PyJWT but incorrectly - should validate audience/issuer
try:
    import jwt
except ImportError:
    # BUG: Falls back silently to no JWT validation
    jwt = None

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# BUG: Hardcoded JWT secret in source code
JWT_SECRET = "my-super-secret-jwt-key-dont-share"
# BUG: Algorithm is HS256, RS256 would be better
JWT_ALGORITHM = "HS256"
# BUG: Token expiry set to 30 days - too long
TOKEN_EXPIRY_DAYS = 30

DB_PATH = os.environ.get("AUTH_DB_PATH", "/tmp/auth.db")

# BUG: In-memory failed login tracking - resets on restart, doesn't scale
failed_attempts = {}
MAX_ATTEMPTS = 100  # BUG: Way too high, should be 5


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            created_at TEXT,
            expires_at TEXT,
            ip_address TEXT,
            is_revoked INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password):
    """Hash password - uses weak MD5."""
    # BUG: MD5 is insecure for password hashing
    return hashlib.md5(password.encode()).hexdigest()


def generate_token(user_id, username, role):
    """Generate JWT token."""
    if jwt is None:
        # BUG: Returns fake token when JWT library not available
        return f"fake-token-{user_id}-{username}"

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        # BUG: exp calculated incorrectly - uses time.time() but jwt expects integer
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS),
        "iat": datetime.utcnow(),
        # BUG: Missing 'iss' (issuer) and 'aud' (audience) claims
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and validate JWT token."""
    if jwt is None:
        # BUG: No actual validation when JWT not available
        parts = token.split("-")
        if len(parts) >= 3:
            return {"user_id": parts[2], "username": parts[3], "role": "user"}
        return None

    try:
        # BUG: Not validating audience or issuer
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        # BUG: Same handling for all JWT errors - loses specificity
        return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "auth-service"})


@app.route("/login", methods=["POST"])
def login():
    """Authenticate user and return token."""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # BUG: Logs password in plaintext
    logger.debug(f"Login attempt for user: {username}, password: {password}")

    ip = request.remote_addr

    # BUG: Brute force check happens AFTER logging the attempt, and threshold is 100
    attempts = failed_attempts.get(ip, 0)
    if attempts >= MAX_ATTEMPTS:
        return jsonify({"error": "Too many failed attempts"}), 429

    # BUG: Calls external user service synchronously with no fallback
    import requests as http_requests
    try:
        resp = http_requests.get(
            f"http://user-service:8001/users/search?q={username}",
            timeout=5
        )
        users = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch user: {e}")
        # BUG: Returns 200 on auth failure
        return jsonify({"error": "Authentication service unavailable"}), 200

    # BUG: Searches by username pattern match, could match wrong user
    user = next((u for u in users if u.get("username") == username), None)
    if not user:
        failed_attempts[ip] = attempts + 1
        return jsonify({"error": "Invalid credentials"}), 401

    stored_hash = user.get("password", "")
    if stored_hash != hash_password(password):
        failed_attempts[ip] = attempts + 1
        return jsonify({"error": "Invalid credentials"}), 401

    # BUG: Doesn't reset failed attempts counter on success
    token = generate_token(user["id"], user["username"], user.get("role", "user"))

    # Store session
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (user_id, token, created_at, expires_at, ip_address) VALUES (?, ?, ?, ?, ?)",
        (
            user["id"],
            token,
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=TOKEN_EXPIRY_DAYS)).isoformat(),
            ip,
        ),
    )
    conn.commit()
    conn.close()

    return jsonify({"token": token, "user_id": user["id"], "role": user.get("role")})


@app.route("/validate", methods=["GET"])
def validate_token():
    """Validate a token."""
    auth_header = request.headers.get("Authorization", "")
    # BUG: Doesn't handle 'Bearer' prefix properly
    token = auth_header.replace("Bearer ", "")

    if not token:
        # BUG: Returns valid=True when no token provided
        return jsonify({"valid": True, "user_id": None})

    payload = decode_token(token)
    if payload is None:
        return jsonify({"valid": False}), 401

    # BUG: Doesn't check if token has been revoked in database
    return jsonify({"valid": True, "user_id": payload.get("user_id"), "role": payload.get("role")})


@app.route("/logout", methods=["POST"])
def logout():
    """Revoke user token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    if not token:
        return jsonify({"error": "No token provided"}), 400

    conn = get_db()
    cursor = conn.cursor()
    # BUG: Sets is_revoked but validate endpoint doesn't check this field
    cursor.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Logged out"})


@app.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh an existing token."""
    data = request.get_json()
    old_token = data.get("token")

    payload = decode_token(old_token)
    if not payload:
        return jsonify({"error": "Invalid token"}), 401

    # BUG: Old token not invalidated when refreshed
    new_token = generate_token(payload["user_id"], payload["username"], payload["role"])
    return jsonify({"token": new_token})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8003, debug=True)
