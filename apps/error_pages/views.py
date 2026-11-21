#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.http import HttpResponse
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.utils.translation import get_language, get_language_bidi
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import requires_csrf_token

# from django_contrib.sites.services import SiteService
from .constants import DEFAULT_ERROR_MESSAGE, ERROR_DATA

ERROR_TEMPLATE_NAME = "error.html"


@requires_csrf_token
@never_cache
def error_page(request, status=500, template_name=ERROR_TEMPLATE_NAME):
    from django.conf import settings

    status = int(status)
    context = ERROR_DATA.get(status, {}).copy()
    context.setdefault("title", "Error")
    context.setdefault("eyebrow", "Request failed")
    context.setdefault("message", DEFAULT_ERROR_MESSAGE)
    context.update(
        {
            "status": status,
            "lang": get_language(),
            "LANGUAGE_BIDI": get_language_bidi(),
            "site_url": "/",
            "STATIC_URL": settings.STATIC_URL,
            "request_path": request.get_full_path(),
        }
    )

    # site = SiteService.get_current_site(request)
    site = None
    if site is not None:
        context.update(
            {
                "site_url": "%(protocol)s://%(domain)s"
                % {
                    "protocol": request.is_secure() and "https" or "http",
                    "domain": site.domain,
                },
                "site": site,
                # 'setting': SiteService.get_site_setting(site),
                # 'social_media': SiteService.get_social_media(site),
            }
        )

    try:
        template = loader.get_template(template_name)
        body = template.render(context)
        content_type = None  # Django will use DEFAULT_CONTENT_TYPE
    except TemplateDoesNotExist:
        if template_name != ERROR_TEMPLATE_NAME:
            # Re-raise if it's a missing custom template.
            raise
        body = "<h1>Error %s</h1>" % status
        content_type = "text/html"

    return HttpResponse(body, status=status, content_type=content_type)


@requires_csrf_token
def page_not_found(request, exception=None):
    return error_page(request, status=404)


@requires_csrf_token
def server_error(request):
    return error_page(request, status=500)


@requires_csrf_token
def bad_request(request, exception=None):
    return error_page(request, status=400)


@requires_csrf_token
def permission_denied(request, exception=None):
    return error_page(request, status=403)


def csrf_failure(request, reason=""):
    return error_page(request, status=403)
