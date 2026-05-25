from .base import *
import os

DEBUG         = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE':   'mssql',
        'NAME':     os.getenv('DB_NAME', 'xantara_pos_db'),
        'USER':     os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST':     os.getenv('DB_HOST', 'localhost'),
        'PORT':     os.getenv('DB_PORT', '1433'),
        'OPTIONS': {
            'driver': os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server'),
            'unicode_results': True,
        },
    }
}

CORS_ALLOW_ALL_ORIGINS = True
