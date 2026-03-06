from pathlib import Path
import os
from django.contrib import messages

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production'

# DEBUG - defaults to True for local development, set to False in production via env var
DEBUG = os.environ.get("DEBUG", "True").lower() not in ("false", "0", "no")

ALLOWED_HOSTS = ['*']


# ========================
# INSTALLED APPS
# ========================

INSTALLED_APPS = [
    'core',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]


# ========================
# MIDDLEWARE
# ========================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]

# Add WhiteNoise middleware in production
if not DEBUG:
    MIDDLEWARE += ['whitenoise.middleware.WhiteNoiseMiddleware']

MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'hospital.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'hospital.wsgi.application'


# ========================
# DATABASE
# ========================

if DEBUG:
    # Local development → SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production → PostgreSQL (Render)
    import dj_database_url
    db_from_env = dj_database_url.config()
    DATABASES = {
        'default': db_from_env
    }


# ========================
# PASSWORD VALIDATION
# ========================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ========================
# INTERNATIONALIZATION
# ========================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ========================
# STATIC FILES
# ========================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ========================
# MEDIA FILES
# ========================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ========================
# DEFAULT PRIMARY KEY
# ========================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ========================
# LOGGING
# ========================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# ========================
# SESSION & MESSAGE
# ========================

SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.WARNING: 'warning',
    messages.SUCCESS: 'info',
    messages.INFO: 'info',
}

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False
CSRF_USE_SESSIONS = False