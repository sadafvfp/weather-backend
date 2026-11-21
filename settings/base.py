#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import os
from django.utils.translation import gettext_lazy as _
from kombu import Exchange, Queue
from datetime import timedelta

# from dotenv import load_dotenv
from datetime import timedelta

# load_dotenv()


def get_env_var(key, default=None):
    return os.environ.get("BACKEND_%s" % key, default)


# Celery settings
# http://docs.celeryproject.org/en/latest/configuration.html
# https://denibertovic.com/posts/celery-best-practices/
# http://celery.readthedocs.org/en/latest/userguide/monitoring.html

# Broker settings
CELERY_BROKER_URL = get_env_var("CELERY_BROKER_URL", "amqp://guest:guest@localhost//")

#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ALWAYS_EAGER = get_env_var("CELERY_TASK_ALWAYS_EAGER", "False") == "True"

CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = "direct"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"
CELERY_ENABLE_UTC = True
# CELERY_TIMEZONE = "UTC"
CELERY_TIMEZONE="Asia/Tehran"
# http://docs.celeryproject.org/en/latest/configuration.html#celery-queues
CELERY_TASK_QUEUES = (
    Queue("default", Exchange("para", type="topic"), routing_key="default"),
)

# http://docs.celeryproject.org/en/latest/configuration.html#celery-routes
# CELERY_TASK_ROUTES = {}

# Whether to store the task return values or not.
CELERY_TASK_IGNORE_RESULT = True

# If you still want to store errors, just not successful return values
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = False

# The backend used to store task results.
# CELERY_RESULT_BACKEND = ''

# Time (in seconds, or a timedelta object) for when after stored task
# tombstones will be deleted.
# CELERY_RESULT_EXPIRES = 0

# Django settings for asil project.

# The top directory for this project. Contains requirements/, manage.py,
# and README.rst, a asil directory with settings etc (see
# PROJECT_PATH), as well as a directory for each Django app added to this
# project.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# The directory with this project's templates, settings, urls, static dir,
# wsgi.py, fixtures, etc.
PROJECT_PATH = os.path.join(PROJECT_ROOT, "backend")

DEBUG = get_env_var("DEBUG", "False") == "True"

TEST = get_env_var("TEST", "False") == "True"

ADMINS = (("Sadaf Vafaeipour", "sadaf.v.78@gmail.com"),)

MANAGERS = ADMINS

ALLOWED_HOSTS = get_env_var("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": get_env_var("DEFAULT_DB_NAME", "weather"),
        "USER": get_env_var("DEFAULT_DB_USER", "postgres"),
        "PASSWORD": get_env_var("DEFAULT_DB_PASSWORD", "sadafsahel"),
        "HOST": get_env_var("DEFAULT_DB_HOST", "host.docker.internal"),
        "PORT": get_env_var("DEFAULT_DB_PORT", "5432"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
# Make this unique, and don't share it with anybody.
SECRET_KEY = get_env_var("SECRET_KEY", "fake-key")

# A list of fallback secret keys for a particular Django installation.
SECRET_KEY_FALLBACKS = get_env_var("SECRET_KEY_FALLBACKS", "").split()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = get_env_var("TIME_ZONE", "Asia/Tehran")

# LOCALE_PATHS = (os.path.join(PROJECT_PATH, "locale"),)

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "fa-ir"

LANGUAGE_COOKIE_AGE = get_env_var(
    "LANGUAGE_COOKIE_AGE"
)  # None => expires at browser close
LANGUAGE_COOKIE_DOMAIN = get_env_var("LANGUAGE_COOKIE_DOMAIN")
LANGUAGE_COOKIE_HTTPONLY = get_env_var("LANGUAGE_COOKIE_HTTPONLY", "False") == "True"
LANGUAGE_COOKIE_NAME = get_env_var("LANGUAGE_COOKIE_NAME", "_lng")
LANGUAGE_COOKIE_PATH = get_env_var("LANGUAGE_COOKIE_PATH", "/")
LANGUAGE_COOKIE_SAMESITE = get_env_var("LANGUAGE_COOKIE_SAMESITE", "Lax")
LANGUAGE_COOKIE_SECURE = get_env_var("LANGUAGE_COOKIE_SECURE", "False") == "True"

SITE_ID = int(get_env_var("SITE_ID", 1))

SITE_URL = get_env_var("SITE_URL", "http://127.0.0.1/")

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/public/media/"
MEDIA_ROOT = get_env_var("MEDIA_ROOT", os.path.join(PROJECT_ROOT, "public", "media"))


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = get_env_var("MEDIA_URL", "/media/")

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/public/static/"
STATIC_ROOT = get_env_var("STATIC_ROOT", os.path.join(PROJECT_ROOT, "public", "static"))

# Path to generated static files from JavaScript catalog
STATICI18N_ROOT = os.path.join(
    PROJECT_PATH,
    "static",
)

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = get_env_var("STATIC_URL", "/static/")

# Additional locations of static files to collect
STATICFILES_DIRS = (os.path.join(PROJECT_PATH, "static"),)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "DIRS": (os.path.join(PROJECT_PATH, "templates"),),
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": (
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
            ),
            # List of callables that know how to import templates from
            # various sources.
            "loaders": (
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ),
        },
    }
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("mobile_number", "email", "username")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# List of compiled regular expression objects representing User-Agent strings
# that are not allowed to visit any page, system-wide.
# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-DISALLOWED_USER_AGENTS
DISALLOWED_USER_AGENTS = []

# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-APPEND_SLASH
APPEND_SLASH = get_env_var("APPEND_SLASH", "True") == "True"

# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-PREPEND_WWW
PREPEND_WWW = get_env_var("PREPEND_WWW", "False") == "True"

# A boolean that specifies whether to output the ETag header.
# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-USE_ETAGS
USE_ETAGS = True

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    # Adds a few conveniences for perfectionists (i.e. URL rewriting)
    "django.middleware.common.CommonMiddleware",
)

# Security Settings
SECURE_BROWSER_XSS_FILTER = get_env_var("SECURE_BROWSER_XSS_FILTER", "True") == "True"
SECURE_CONTENT_TYPE_NOSNIFF = (
    get_env_var("SECURE_CONTENT_TYPE_NOSNIFF", "True") == "True"
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    get_env_var("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
)
SECURE_HSTS_SECONDS = get_env_var("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_PRELOAD = get_env_var("SECURE_HSTS_PRELOAD", "False") == "True"
SECURE_SSL_REDIRECT = get_env_var("SECURE_SSL_REDIRECT", "False") == "True"
SECURE_SSL_HOST = get_env_var("SECURE_SSL_HOST")
SECURE_REDIRECT_EXEMPT = get_env_var("SECURE_REDIRECT_EXEMPT", "").split(",")

USE_X_FORWARDED_HOST = get_env_var("USE_X_FORWARDED_HOST", "False") == "True"
USE_X_FORWARDED_PORT = get_env_var("USE_X_FORWARDED_PORT", "False") == "True"
if get_env_var("SECURE_PROXY_SSL_HEADER", "False") == "True":  # pragma: no cover
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": get_env_var("SESSION_REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_KEY_PREFIX = get_env_var("CACHE_MIDDLEWARE_KEY_PREFIX", "middleware")
CACHE_MIDDLEWARE_SECONDS = 600
LOGIN_URL = get_env_var("LOGIN_URL", "/login")

ROOT_URLCONF = "backend.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "backend.wsgi.application"

FIXTURE_DIRS = (os.path.join(PROJECT_PATH, "fixtures"),)

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "DEBUG" if DEBUG else "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "DEBUG" if DEBUG else "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": os.path.join(PROJECT_PATH, "logs", "backend.log"),
            "maxBytes": 20 * 1024 * 1024,  # 20 MBs
            "backupCount": 40,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"] if DEBUG else ["file"],
            "propagate": True,
            "level": "WARNING" if DEBUG else "ERROR",
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "WARNING" if DEBUG else "ERROR",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "DEBUG" if DEBUG else "WARNING",
            "handlers": ["console"] if DEBUG else ["file"],
        },
        "asil": {
            "handlers": ["console"] if DEBUG else ["file"],
            "level": "DEBUG" if DEBUG else "ERROR",
            "propagate": True,
        },
    },
}

INSTALLED_APPS = (
    # Internal Django Apps
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "backend.apps.accounts",
    "backend.apps.device",
    "backend.apps.mytimescale",
    "backend.apps.error_pages",
    # "django.contrib.sites",
    # Include app here if you use custom User
    # External Apps
    # "django_cleanup",
    # Project Apps
)


# if DEBUG:  # pragma: no cover
#     INSTALLED_APPS += ("django_extensions",)

# PHONENUMBER_DEFAULT_REGION = get_env_var("PHONENUMBER_DEFAULT_REGION")
#  A temporary file is used when upload exceeds FILE_UPLOAD_MAX_MEMORY_SIZE.
# See also https://docs.djangoproject.com/en/3.0/ref/settings/#file-upload-max-memory-size
FILE_UPLOAD_MAX_MEMORY_SIZE = int(get_env_var("FILE_UPLOAD_MAX_MEMORY_SIZE", 2621440))
# If this isn’t given or is None, you’ll get operating-system dependent behavior.
# On most platforms, temporary files will have a mode of 0o600,
# and files saved from memory will be saved using the system’s standard umask.
# In django 3.0 the default is 0o644
# In older versions, the default value is None.
# See also https://docs.djangoproject.com/en/3.0/ref/settings/#file-upload-permissions
FILE_UPLOAD_PERMISSIONS = 0o644
UPLOAD_PATH = get_env_var("UPLOAD_PATH", "ups/")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Subject-line prefix for email messages sent.
EMAIL_SUBJECT_PREFIX = _("[Asil] ")

DEFAULT_FROM_EMAIL = "Salehian <noreply@salehianasil.com>"

SERVER_EMAIL = "server@salehianasil.com"

# Set model for using in authentication
AUTH_USER_MODEL = "accounts.User"

CSRF_COOKIE_AGE = int(
    get_env_var("CSRF_COOKIE_AGE", 2 * 24 * 60 * 60)
)  # Default: 2 days
CSRF_COOKIE_DOMAIN = get_env_var("CSRF_COOKIE_DOMAIN")
CSRF_COOKIE_HTTPONLY = get_env_var("CSRF_COOKIE_HTTPONLY", "False") == "True"
CSRF_COOKIE_NAME = get_env_var("CSRF_COOKIE_NAME", "csrftoken")
CSRF_COOKIE_PATH = get_env_var("CSRF_COOKIE_PATH", "/")
CSRF_COOKIE_SAMESITE = get_env_var("CSRF_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SECURE = get_env_var("CSRF_COOKIE_SECURE", "False") == "True"
# CSRF_FAILURE_VIEW = "backend.apps.error_pages.views.csrf_failure"

# Controls where Django stores session data.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = get_env_var("SESSION_CACHE_ALIAS", "default")
# redis://[:password@]host[:port][/db-number][?option=value]
# unix://[:password]@/path/to/socket.sock[?option=value]
# SESSION_REDIS = {"url": get_env_var("SESSION_REDIS_URL", "redis://localhost:6379/1")}

SESSION_COOKIE_AGE = int(
    get_env_var("SESSION_COOKIE_AGE", 2 * 24 * 60 * 60)
)  # Default: 2 days
SESSION_COOKIE_DOMAIN = get_env_var("SESSION_COOKIE_DOMAIN")
SESSION_COOKIE_HTTPONLY = get_env_var("SESSION_COOKIE_HTTPONLY", "True") == "True"
SESSION_COOKIE_NAME = get_env_var("SESSION_COOKIE_NAME", "sessionid")
SESSION_COOKIE_PATH = get_env_var("SESSION_COOKIE_PATH", "/")
SESSION_COOKIE_SAMESITE = get_env_var("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = get_env_var("SESSION_COOKIE_SECURE", "False") == "True"

SESSION_EXPIRE_AT_BROWSER_CLOSE = (
    get_env_var("SESSION_EXPIRE_AT_BROWSER_CLOSE", "True") == "True"
)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# The host to use for sending email.
EMAIL_HOST = get_env_var("EMAIL_HOST", "smtp.mailgun.org")

# Username to use for the SMTP server defined in EMAIL_HOST.
EMAIL_HOST_USER = get_env_var("EMAIL_HOST_USER", "")

# Password to use for the SMTP server defined in EMAIL_HOST.
EMAIL_HOST_PASSWORD = get_env_var("EMAIL_HOST_PASSWORD", "")

# Port to use for the SMTP server defined in EMAIL_HOST.
EMAIL_PORT = get_env_var("EMAIL_PORT", 587)

# Whether to use a TLS (secure) connection when talking to the SMTP server.
EMAIL_USE_TLS = get_env_var("EMAIL_USE_TLS", "True") == "True"

# Integer sensor error codes for OSPM three-minute ingestion/API ``error_code`` field.
# error_code=0 means all sensors are healthy; map nonzero codes to Persian labels for APIs.
# Extend or override this dict in deployment settings as needed.
OSPM_SENSOR_ERROR_CODES = {
    1: "پمپ",
    2: "سنسور لایت اسکتر",
    4: "سنسور دما",
    8: "سنسور ذرات یا ارتباط آن با برد",
    12:"سنسور دما و سنسور ذرات",
}
