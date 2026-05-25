from .base import *
import os

DEBUG         = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
DATABASES = {
    'default': {
        'ENGINE':   'mssql',
        'NAME':     os.getenv('DB_NAME'),
        'USER':     os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST':     os.getenv('DB_HOST'),
        'PORT':     os.getenv('DB_PORT', '1433'),
        'OPTIONS': {
            'driver': os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server'),
            'unicode_results': True,
        },
    }
}
CORS_ALLOWED_ORIGINS        = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
SECURE_BROWSER_XSS_FILTER   = True
X_FRAME_OPTIONS             = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
