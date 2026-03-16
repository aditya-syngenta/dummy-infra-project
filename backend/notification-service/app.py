"""
Notification Service
Sends email and SMS notifications to users.

BUG: Credentials stored in environment with insecure fallbacks
BUG: No retry logic for failed sends
BUG: Email template injection vulnerability
BUG: No rate limiting on notifications
BUG: SMS provider API key hardcoded
BUG: No deduplication - same notification sent multiple times
"""

import os
import json
import logging
import smtplib
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# BUG: Hardcoded SMTP credentials as fallback
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "noreply@dummycompany.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "smtp-password-123!")  # BUG: Default plaintext password

# BUG: Hardcoded Twilio credentials
TWILIO_ACCOUNT_SID = "TWILIO-FAKE-SID-FOR-TESTING-ONLY"
TWILIO_AUTH_TOKEN = "TWILIO-FAKE-TOKEN-FOR-TESTING-ONLY"
TWILIO_FROM_NUMBER = "+15555555555"

DB_PATH = os.environ.get("NOTIF_DB_PATH", "/tmp/notifications.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TEXT,
            error TEXT,
            retry_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def send_email(to_email, subject, body, html_body=None):
    """Send email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    # BUG: Plain text email includes raw HTML if html_body provided
    text_part = MIMEText(body, "plain")
    msg.attach(text_part)

    if html_body:
        # BUG: Template injection - user-controlled data in HTML without sanitization
        html_part = MIMEText(f"<html><body>{html_body}</body></html>", "html")
        msg.attach(html_part)

    try:
        # BUG: No TLS verification
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        # BUG: No retry on failure
        return False


def send_sms(to_number, message):
    """Send SMS via Twilio."""
    try:
        import requests
        # BUG: Credentials in URL (visible in logs)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        data = {
            "From": TWILIO_FROM_NUMBER,
            "To": to_number,
            "Body": message,
        }
        response = requests.post(
            url,
            data=data,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        )
        # BUG: Not checking response status properly
        return response.json()
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "notification-service"})


@app.route("/notify/email", methods=["POST"])
def notify_email():
    """Send email notification."""
    data = request.get_json()

    # BUG: No input validation
    to_email = data.get("to")
    subject = data.get("subject", "Notification")
    body = data.get("body", "")
    # BUG: Accepts arbitrary HTML from user input
    html_body = data.get("html_body")
    user_id = data.get("user_id")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (user_id, type, recipient, subject, body, status) VALUES (?, 'email', ?, ?, ?, 'sending')",
        (user_id, to_email, subject, body),
    )
    notif_id = cursor.lastrowid
    conn.commit()

    success = send_email(to_email, subject, body, html_body)

    status = "sent" if success else "failed"
    cursor.execute(
        "UPDATE notifications SET status = ?, sent_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), notif_id),
    )
    conn.commit()
    conn.close()

    # BUG: Returns 200 even when email sending failed
    return jsonify({"notification_id": notif_id, "status": status}), 200


@app.route("/notify/sms", methods=["POST"])
def notify_sms():
    """Send SMS notification."""
    data = request.get_json()
    to_number = data.get("to")
    message = data.get("message", "")
    user_id = data.get("user_id")

    # BUG: No phone number validation
    result = send_sms(to_number, message)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (user_id, type, recipient, body, status, sent_at) VALUES (?, 'sms', ?, ?, ?, ?)",
        (user_id, to_number, message, "sent" if result else "failed", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "sent" if result else "failed"})


@app.route("/notify/bulk", methods=["POST"])
def bulk_notify():
    """Send bulk notifications."""
    data = request.get_json()
    notifications = data.get("notifications", [])

    results = []
    # BUG: No concurrency - processes notifications sequentially
    # BUG: No batch size limit - could process millions at once
    for notif in notifications:
        if notif.get("type") == "email":
            success = send_email(
                notif["to"],
                notif.get("subject", ""),
                notif.get("body", ""),
            )
            results.append({"to": notif["to"], "success": success})
        elif notif.get("type") == "sms":
            result = send_sms(notif["to"], notif.get("message", ""))
            results.append({"to": notif["to"], "success": bool(result)})

    # BUG: Partial failures not reported correctly - always returns 200
    return jsonify({"results": results, "total": len(notifications), "sent": len(results)})


@app.route("/notifications/<int:user_id>", methods=["GET"])
def get_user_notifications(user_id):
    """Get notification history for a user."""
    # BUG: No authentication check - anyone can view any user's notifications
    conn = get_db()
    cursor = conn.cursor()
    # BUG: No limit on returned records
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (user_id,))
    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(notifications)


if __name__ == "__main__":
    init_db()
    # BUG: Debug mode in production
    app.run(host="0.0.0.0", port=8004, debug=True)
