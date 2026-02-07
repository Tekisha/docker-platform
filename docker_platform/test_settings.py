from docker_platform.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'scm_db'),
        'USER': os.getenv('POSTGRES_USER', 'scm_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'scm_pass'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Disable password hashing for faster user creation in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations (already set in pytest.ini, but belt and suspenders)
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Speed up tests by reducing logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'CRITICAL',
        },
    },
}

# ============== WORKER ISOLATION ==============
WORKER_ID = os.environ.get('PYTEST_XDIST_WORKER', 'master')

if WORKER_ID != 'master':
    # Extract worker number from 'gw0', 'gw1', etc.
    WORKER_NUM = int(WORKER_ID.replace('gw', ''))
else:
    WORKER_NUM = 0

# Disable template caching for tests
for template_engine in TEMPLATES:
    template_engine['OPTIONS']['debug'] = True

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{os.getenv("REDIS_HOST", "redis")}:6379/{WORKER_NUM}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': f'test_{WORKER_ID}',
        'TIMEOUT': 300,
    }
}