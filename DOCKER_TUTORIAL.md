# Docker CLI Tutorial

Simple guide for using Docker CLI with the registry at `localhost`.

## Authentication

### Login
```bash
docker login localhost
# Enter your Django username and password
# User has to be created in the Django app first
# john / password123
```

### Logout
```bash
docker logout localhost
```

## Working with Images

### Tag an existing image
```bash
# Tag for user repository
docker tag myapp:latest localhost/john/myapp:v1.0

# Tag for official repository (admin only)
docker tag myapp:latest localhost/myapp:v1.0
```

### Push to registry
```bash
# Push user repository
docker push localhost/john/myapp:v1.0

# Push official repository
docker push localhost/myapp:v1.0
```

### Pull from registry
```bash
# Pull user repository
docker pull localhost/john/myapp:v1.0

# Pull official repository
docker pull localhost/myapp:v1.0
```

### Remove local image
```bash
# Remove tagged image
docker rmi localhost/john/myapp:v1.0

# Force remove
docker rmi -f localhost/john/myapp:v1.0
```

## Repository Formats

- **User repos**: `localhost/username/appname`
- **Official repos**: `localhost/appname` (admin only)

## Example Workflow
```bash
# 1. Login
docker login localhost

# 2. Tag your image
docker tag nginx:alpine localhost/john/my-nginx:latest

# 3. Push to registry
docker push localhost/john/my-nginx:latest

# 4. Pull on another machine
docker pull localhost/john/my-nginx:latest

# 5. Clean up
docker rmi localhost/john/my-nginx:latest
```
