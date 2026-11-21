#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from .base import *  # NOQA

ROOT_URLCONF = "backend.urls.api"

USE_I18N = True

LANGUAGES = (
    ("en-us", _("English")),
    ("fa", _("Farsi")),
)

TEMPLATES[0]["OPTIONS"] = {
    "debug": DEBUG,
    "context_processors": (
        "django.template.context_processors.i18n",
        "django.template.context_processors.static",
    ),
    # List of callables that know how to import templates from
    # various sources.
    "loaders": (
        "django.template.loaders.filesystem.Loader",
        "django.template.loaders.app_directories.Loader",
    ),
}

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "backend.middleware.DisablePatchMiddleware",
    # Adds a few conveniences for perfectionists (i.e. URL rewriting)
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Adds protection against Cross Site Request Forgeries
    "django.middleware.csrf.CsrfViewMiddleware",
    # Adds the user attribute, representing the currently-logged-in user
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Enables cookie- and session-based message support.
    "django.contrib.messages.middleware.MessageMiddleware",
    # Simple clickjacking protection via the X-Frame-Options header.
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

INSTALLED_APPS += (
    # Internal django apps
    "django.contrib.sessions",
    "rest_framework",
    # Third party apps
    "corsheaders",
    "django_filters",
    # "django_contrib.amp",
    # Project apps
    "backend.apps.custom",
    "backend.apps.aqi",
    
    # "catalog.sitemaps",
)


def get_drf_env_var(key, default=None):
    return get_env_var("DRF_%s" % key, default)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "backend.authentication.SessionAuthentication401",
    ),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_FILTER_BACKENDS": [],
    "DEFAULT_PAGINATION_CLASS": "backend.apps.custom.pagination.LargeResultsSetPagination",
    "PAGE_SIZE": get_drf_env_var("PAGE_SIZE", 24),
    "SEARCH_PARAM": get_drf_env_var("SEARCH_PARAM", "search"),
    "ORDERING_PARAM": get_drf_env_var("ORDERING_PARAM", "ordering"),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_VERSION": get_drf_env_var("DEFAULT_VERSION", "1.0"),
    "ALLOWED_VERSIONS": [
        v for v in get_drf_env_var("ALLOWED_VERSIONS", "1.0").split(",") if v
    ],
    "VERSION_PARAM": get_drf_env_var("VERSION_PARAM", "version"),
    "URL_FORMAT_OVERRIDE": get_drf_env_var("URL_FORMAT_OVERRIDE", "format"),
    "FORMAT_SUFFIX_KWARG": get_drf_env_var("FORMAT_SUFFIX_KWARG", "format"),
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "NON_FIELD_ERRORS_KEY": get_drf_env_var("NON_FIELD_ERRORS_KEY", "non_field_errors"),
}

if DEBUG:  # pragma: no cover
    REST_FRAMEWORK.update(
        {
            "DEFAULT_RENDERER_CLASSES": [
                "rest_framework.renderers.JSONRenderer",
                "rest_framework.renderers.BrowsableAPIRenderer",
            ],
            "DEFAULT_PARSER_CLASSES": [
                "rest_framework.parsers.JSONParser",
                "rest_framework.parsers.FormParser",
                "rest_framework.parsers.MultiPartParser",
            ],
        }
    )
    # INSTALLED_APPS += ("drf_yasg",)
# CustomResponseSerializer
REST_AUTH = {
    "SESSION_LOGIN": True,  # log in with a Django session
    "USE_JWT": False,
    "TOKEN_MODEL": None,
    # don't create or return auth tokens
    # /auth/user/ uses the same rule as /accounts/profile/: username only.
    "USER_DETAILS_SERIALIZER": "backend.apps.accounts.serializers.user.ProfileSerializer",
}
# Django cors headers settings
# CORS_ORIGIN_ALLOW_ALL = get_env_var("CORS_ORIGIN_ALLOW_ALL", "False") == "True"

# # cors domains
# CORS_ORIGIN_WHITELIST = [
#     i for i in get_env_var("CORS_ORIGIN_WHITELIST", "").split(",") if i
# ]

# CORS_ORIGIN_REGEX_WHITELIST = [
#     i for i in get_env_var("CORS_ORIGIN_REGEX_WHITELIST", "").split(",") if i
# ]

# CORS_ALLOW_METHODS = [i for i in get_env_var("CORS_ALLOW_METHODS", "").split(",") if i]

# CORS_ALLOW_CREDENTIALS = get_env_var("CORS_ALLOW_CREDENTIALS", "True") == "True"
# def _env_origin_list(key, default=""):
#     return [i.strip() for i in get_env_var(key, default).split(",") if i.strip()]


# FRONTEND_PUBLIC_ORIGIN = get_env_var("FRONTEND_PUBLIC_ORIGIN", "").strip()

# if DEBUG:
#     FRONTEND_ORIGINS = [
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#         "http://host.docker.internal:5173",
#     ]
# elif FRONTEND_PUBLIC_ORIGIN:
#     FRONTEND_ORIGINS = [FRONTEND_PUBLIC_ORIGIN]
# else:
#     FRONTEND_ORIGINS = []

# CORS: which frontend origins may call the API from the browser
# _cors_from_env = _env_origin_list("CORS_ORIGIN_WHITELIST")
CORS_ALLOWED_ORIGINS =  [i for i in get_env_var("CORS_ALLOWED_ORIGINS", "").split(",") if i]
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

# /_csrf_default = (
#     ",".join(FRONTEND_ORIGINS)
#     if FRONTEND_ORIGINS
#     else "http://localhost:5173,http://127.0.0.1:5173"
# )
CSRF_TRUSTED_ORIGINS =[i for i in get_env_var("CSRF_TRUSTED_ORIGINS", "").split(",") if i]
# [
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
# ]


def get_jwt_env_var(key, default=None):
    return get_env_var("JWT_%s" % key, default)


# SIMPLE_JWT = {
#     # 5 minutes
#     "ACCESS_TOKEN_LIFETIME": timedelta(
#         seconds=int(get_jwt_env_var("ACCESS_TOKEN_LIFETIME_SECONDS", 5 * 60))
#     ),
#     "REFRESH_TOKEN_LIFETIME": timedelta(
#         seconds=int(get_jwt_env_var("REFRESH_TOKEN_LIFETIME_SECONDS", 24 * 60 * 60))
#     ),
#     "ROTATE_REFRESH_TOKENS": get_jwt_env_var("ROTATE_REFRESH_TOKENS", "False")
#     == "True",
#     "BLACKLIST_AFTER_ROTATION": get_jwt_env_var("BLACKLIST_AFTER_ROTATION", "True")
#     == "True",
#     "UPDATE_LAST_LOGIN": True,
#     "ALGORITHM": get_jwt_env_var("ALGORITHM", "HS256"),
#     "SIGNING_KEY": get_jwt_env_var("SIGNING_KEY", SECRET_KEY),
#     "VERIFYING_KEY": get_jwt_env_var("VERIFYING_KEY", None),
#     "AUDIENCE": None,
#     "ISSUER": None,
#     "JWK_URL": None,
#     "LEEWAY": int(get_jwt_env_var("LEEWAY", 0)),
#     "AUTH_HEADER_TYPES": ("Bearer",),
#     "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
#     "USER_ID_FIELD": get_jwt_env_var("USER_ID_FIELD", "uuid"),
#     "USER_ID_CLAIM": get_jwt_env_var("USER_ID_CLAIM", "user_id"),
#     "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
#     "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
#     "TOKEN_TYPE_CLAIM": get_jwt_env_var("TOKEN_TYPE_CLAIM", "token_type"),
#     "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
#     "JTI_CLAIM": get_jwt_env_var("JTI_CLAIM", "jti"),
#     "SLIDING_TOKEN_REFRESH_EXP_CLAIM": get_jwt_env_var(
#         "SLIDING_TOKEN_REFRESH_EXP_CLAIM", "refresh_exp"
#     ),
#     "SLIDING_TOKEN_LIFETIME": timedelta(
#         seconds=int(get_jwt_env_var("SLIDING_TOKEN_LIFETIME_SECONDS", 5 * 60))
#     ),
#     "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(
#         seconds=int(
#             get_jwt_env_var("SLIDING_TOKEN_REFRESH_LIFETIME_SECONDS", 24 * 60 * 60)
#         )
#     ),
# }

DRF_RECAPTCHA_VERIFY_ENDPOINT = get_env_var(
    "DRF_RECAPTCHA_VERIFY_ENDPOINT", "https://www.google.com/recaptcha/api/siteverify"
)
DRF_RECAPTCHA_SECRET_KEY = get_env_var("DRF_RECAPTCHA_SECRET_KEY")

GA_VERSION = get_env_var("GA_VERSION", "GA1")

GA_COOKIE_NAME = get_env_var("GA_COOKIE_NAME", "_ga")
GA_COOKIE_AGE = int(get_env_var("GA_COOKIE_AGE", 2 * 365 * 24 * 60 * 60))  # 2 years
GA_COOKIE_PATH = get_env_var("GA_COOKIE_PATH", "/")
GA_COOKIE_DOMAIN = get_env_var("GA_COOKIE_DOMAIN")
GA_COOKIE_SECURE = get_env_var("GA_COOKIE_SECURE", "False") == "True"
GA_COOKIE_HTTPONLY = get_env_var("GA_COOKIE_HTTPONLY", "False") == "True"
GA_COOKIE_SAMESITE = get_env_var("GA_COOKIE_SAMESITE", "Lax")

GTM_AMP_CONF_URL = get_env_var(
    "GTM_AMP_CONF_URL", "https://www.googletagmanager.com/amp.json"
)
GTM_CONFIG_CACHE_TIMEOUT = int(
    get_env_var("GTM_CONFIG_CACHE_TIMEOUT", 10 * 60)
)  # 10 minutes

AMP_CONFIG_CORS_ORIGIN_WHITELIST = [
    i for i in get_env_var("AMP_CONFIG_CORS_ORIGIN_WHITELIST", "").split(",") if i
]
SESSION_CACHE_ALIAS = "default"
