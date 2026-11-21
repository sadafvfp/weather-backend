#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.urls import path, include
from django.views.i18n import JavaScriptCatalog
from django.contrib import admin

from . import urlpatterns
# from ..views import RobotsBlockView

admin.autodiscover()

# handler403 = "backend.apps.error_pages.views.permission_denied"
# handler404 = "backend.apps.error_pages.views.page_not_found"
# handler500 = "backend.apps.error_pages.views.server_error"

urlpatterns += [
    #     path(
    #         "attributes/", include("catalog.attributes.urls.admin", namespace="attributes")
    #     ),
    #     path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    #     path("ckeditor/", include("ckeditor_uploader.urls")),
    #     path("", include("django_contrib.recaptcha.urls", namespace="recaptcha")),
    #     path("robots.txt", RobotsBlockView.as_view(), name="robots"),
    # Django Admin
    path("", admin.site.urls),
]
