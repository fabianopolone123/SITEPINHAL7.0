import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 't', 'yes', 'y', 'on')


def _env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


# In production, override these via environment variables.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-pinhal-junior-change-me')
DEBUG = _env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS: list[str] = _env_list('DJANGO_ALLOWED_HOSTS', [])
CSRF_TRUSTED_ORIGINS: list[str] = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS', [])


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'ui' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

_database_url = os.environ.get('DJANGO_DATABASE_URL', '').strip()
_sqlite_path = os.environ.get('DJANGO_SQLITE_PATH', '').strip()

if _database_url:
    parsed = urlparse(_database_url)
    if parsed.scheme in ('postgres', 'postgresql'):
        # Requires psycopg/psycopg2 installed in the environment.
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': (parsed.path or '').lstrip('/'),
            'USER': parsed.username or '',
            'PASSWORD': parsed.password or '',
            'HOST': parsed.hostname or '',
            'PORT': str(parsed.port or 5432),
        }
    elif parsed.scheme == 'sqlite':
        # Example: sqlite:////srv/sitepinhal/data/db.sqlite3
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': parsed.path,
        }
elif _sqlite_path:
    DATABASES['default']['NAME'] = _sqlite_path


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR.parent / 'ui' / 'static']
STATIC_ROOT = Path(os.environ.get('DJANGO_STATIC_ROOT')) if os.environ.get('DJANGO_STATIC_ROOT') else BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('DJANGO_MEDIA_ROOT')) if os.environ.get('DJANGO_MEDIA_ROOT') else BASE_DIR.parent / 'media'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:confirmacao'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# When behind a proxy (nginx), this lets Django know the request scheme is HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG and _env_bool('DJANGO_SECURE_SSL_REDIRECT', False):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
