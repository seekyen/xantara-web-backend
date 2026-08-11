from .base import *
import os

DEBUG = False


def env_list(name):
    return [value.strip() for value in os.getenv(name, '').split(',') if value.strip()]


ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')

database_engine = os.getenv('DB_ENGINE', 'mysql').strip().lower()
if database_engine == 'mssql':
    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '1433'),
            'OPTIONS': {
                'driver': os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server'),
                'unicode_results': True,
            },
        }
    }
elif database_engine == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }
else:
    raise ValueError('DB_ENGINE must be either mysql or mssql')

CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'true').lower() == 'true'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
