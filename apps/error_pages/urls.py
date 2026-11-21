#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.urls import re_path

from .constants import ERROR_DATA
from .views import error_page

handler403 = "backend.apps.error_pages.views.permission_denied"
handler404 = "backend.apps.error_pages.views.page_not_found"
handler500 = "backend.apps.error_pages.views.server_error"

app_name = "error_pages"

error_statuses = "|".join([str(status) for status in ERROR_DATA.keys()])

urlpatterns = [
    re_path(r"^(?P<status>%s).html$" % error_statuses, error_page, name="page"),
]
