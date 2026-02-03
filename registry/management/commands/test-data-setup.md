# Test Data Management Commands

## create_test_data.py

Django management command for generating large-scale test data to populate the database with sample repositories, users, stars, and tags.

### Purpose

This command creates realistic test data for development, testing, and performance benchmarking, including:
- Configurable number of test users with different roles and publisher statuses
- Official repositories (Ubuntu, Nginx, Python, Node, Postgres, etc.)
- User-generated repositories with randomized names and descriptions
- Star relationships between users and repositories
- Realistic pull counts and update timestamps

### Usage

```bash
# Default: 50 users, ~5 repos per user
python manage.py create_test_data

# Custom: 100 users, ~10 repos per user
python manage.py create_test_data --users 100 --repos-per-user 10

# Small dataset for quick testing
python manage.py create_test_data --users 10 --repos-per-user 3
```

### Command Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--users` | int | 50 | Number of users to create |
| `--repos-per-user` | int | 5 | Average number of repositories per user (actual: ±2-3) |


### Created Users
- **Regular users**: `testuser1`, `testuser2`, ..., `testuserN`
  - Password: `lozinka123`
  - Publisher status distribution:
    - 70% regular users (no badge)
    - 20% verified publishers
    - 10% sponsored OSS
- **Admin user**: `testadmin`
  - Password: `lozinka123`
  - Role: ADMIN
  - Owner of official repositories

