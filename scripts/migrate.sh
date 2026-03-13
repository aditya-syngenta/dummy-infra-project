#!/bin/bash
# Database migration script
# BUG: No transaction wrapping - partial migrations leave DB in inconsistent state
# BUG: No migration versioning/tracking
# BUG: Runs as superuser instead of limited migration user
# BUG: No dry-run mode

# BUG: Hardcoded database credentials
DB_HOST="dummy-infra-prod-db.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="appdb"
DB_USER="postgres"
# BUG: Password in plaintext
DB_PASSWORD="Passw0rd123!"

export PGPASSWORD=$DB_PASSWORD

echo "Starting database migrations..."

# BUG: No backup before migration
# BUG: No check if migrations already applied

# Migration 001: Create users table
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    -- BUG: No UNIQUE constraint on email
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
-- BUG: No index on email or username column
EOF

# Migration 002: Create orders table
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    -- BUG: Missing FOREIGN KEY constraint to users table
    items JSONB NOT NULL,
    total_price DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    shipping_address TEXT,
    payment_method VARCHAR(100),
    discount_code VARCHAR(50)
);
-- BUG: No index on user_id or status
EOF

# Migration 003: Create sessions table
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    ip_address VARCHAR(45),
    is_revoked BOOLEAN DEFAULT FALSE
    -- BUG: No index on token column - slow lookups
    -- BUG: No FOREIGN KEY to users table
);
EOF

# Migration 004: Insert default admin user
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
-- BUG: Inserts admin user with hardcoded MD5 hashed password
-- MD5 of "admin123"
INSERT INTO users (username, email, password, role)
VALUES ('admin', 'admin@dummyinfra.com', '0192023a7bbd73250516f069df18b500', 'admin')
ON CONFLICT DO NOTHING;
-- BUG: "ON CONFLICT DO NOTHING" silently skips if admin already exists with different password
EOF

# BUG: No verification that migrations succeeded
echo "Migrations complete!"

# BUG: Leaves PGPASSWORD set in environment
unset PGPASSWORD
