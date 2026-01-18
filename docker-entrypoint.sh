#!/bin/bash
set -e

echo "Starting Django application..."

# Validate required environment variables
required_vars=("POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD" "SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

echo "Environment variables validated successfully"

# Wait for database to be ready
echo "Waiting for database..."
while ! python -c "
import os
import psycopg
try:
    conn = psycopg.connect(
        host=os.getenv('POSTGRES_HOST', 'db'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'scm_db'),
        user=os.getenv('POSTGRES_USER', 'scm_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'scm_pass')
    )
    conn.close()
except:
    exit(1)
"; do
    echo "Database is unavailable - sleeping..."
    sleep 2
done

echo "Database is ready!"

# Create secrets directory if it doesn't exist
mkdir -p /app/secrets

# Run database migrations
echo "Running migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Django application is ready!"

# Execute the main command
exec "$@"
