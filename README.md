# Docker Registry Platform

A Django-based Docker registry management platform with user authentication, repository management, and administrative features.

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

The application will be available at: **http://localhost:8000**

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

# Database shell
docker-compose exec db psql -U scm_user -d scm_db
```

## Manual Setup (Without Docker)

If you prefer to run without Docker:

### Prerequisites
- Python 3.10+
- PostgreSQL

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
export SUPERADMIN_PASS_FILE=./secrets/superadmin_password.txt

# Database setup
python manage.py migrate
python manage.py setup_system --flush

# Run server
python manage.py runserver
```

### Creating Migrations
```bash
docker-compose run --rm web python manage.py makemigrations
docker-compose run --rm web python manage.py migrate
```
