# Docker Registry Platform

A Django-based Docker registry management platform with user authentication, repository management, and administrative features. Uses nginx as a reverse proxy to route traffic between the Django web application and Docker Registry.

## Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose

### 1. Environment Setup

Copy the environment template and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your database password and other settings:
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web,0.0.0.0

POSTGRES_DB=scm_db
POSTGRES_USER=scm_user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

SUPERADMIN_USERNAME=superadmin
SUPERADMIN_EMAIL=admin@example.com
SUPERADMIN_PASS_FILE=/app/secrets/superadmin_password.txt
```

### 2. Initial Setup

Setup database, groups, permissions, and create superadmin:

```bash
docker-compose run --rm web python manage.py setup_system --flush
```

### 3. Start the Application

```bash
docker-compose up -d
```

The application will be available at: **http://localhost** (nginx serves on port 80)

- **Web Interface**: http://localhost (Django app)
- **Docker Registry**: http://localhost/v2/ (Docker Registry API)
- **Direct Django**: http://localhost:8000 (bypasses nginx)

### 4. Get Admin Credentials

```bash
cat ./secrets/superadmin_password.txt
```

- **Username**: `superadmin` (or whatever you set in SUPERADMIN_USERNAME)
- **Password**: Generated automatically and saved to the secrets file

## Common Commands

### Application Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f web

# Restart web service
docker-compose restart web
```

### Development
```bash
# Run tests
docker-compose run --rm web python manage.py test

# Django shell
docker-compose run --rm web python manage.py shell

# Access container shell
docker-compose exec web bash

# Run migrations
docker-compose run --rm web python manage.py migrate
```

### Database Operations
```bash
# Reset everything (removes all data)
docker-compose run --rm web python manage.py setup_system --flush

# Setup without data loss (idempotent)
docker-compose run --rm web python manage.py setup_system

# Create new migrations after model changes
docker-compose run --rm web python manage.py makemigrations

# Apply migrations
docker-compose run --rm web python manage.py migrate

# Database shell
docker-compose exec db psql -U scm_user -d scm_db
```

## Architecture

The platform uses nginx as a reverse proxy:
- **nginx** (port 80) - Routes traffic between Django and Docker Registry
- **Django** (port 8000) - Web application and API
- **Docker Registry** (port 5000) - Docker image storage
- **PostgreSQL** (port 5432) - Database

## Manual Setup (Without Docker)

If you prefer to run without Docker:

### Prerequisites
- Python 3.10+
- PostgreSQL

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (change POSTGRES_HOST=db to POSTGRES_HOST=localhost in .env)
export SUPERADMIN_PASS_FILE=./secrets/superadmin_password.txt

# Database setup
python manage.py makemigrations
python manage.py migrate
python manage.py setup_system --flush

# Run server (use port 8001 to avoid conflicts with Docker setup)
python manage.py runserver 8001
```

**Note**: When running locally, the app will be available at **http://localhost:8001**

## Development Workflow

### Working with Database Migrations

**With Docker:**
```bash
# Create new migrations after model changes
docker-compose run --rm web python manage.py makemigrations

# Apply migrations
docker-compose run --rm web python manage.py migrate
```

**Locally:**
```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Running Tests

**With Docker:**
```bash
# Run all tests
docker-compose run --rm web python manage.py test

# Run specific test file
docker-compose run --rm web python manage.py test registry.tests.test_repositories

# Run with pytest
docker-compose run --rm web python -m pytest
```

**Locally:**
```bash
# Ensure database is set up for tests
python manage.py migrate

# Run all tests
python manage.py test

# Run with pytest
python -m pytest
```

### Port Configuration Summary

- **Docker (with nginx)**: http://localhost (port 80)
- **Docker (direct Django)**: http://localhost:8000
- **Local development**: http://localhost:8001 (recommended to avoid conflicts)
- **PostgreSQL**: localhost:5432
