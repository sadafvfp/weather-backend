#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.urls import include, path
from django.core.exceptions import PermissionDenied
from django.template.exceptions import TemplateDoesNotExist
from django.test import override_settings, TestCase, RequestFactory, Client
from django.utils.encoding import force_bytes

from ..views import error_page, server_error, bad_request
from ..constants import ERROR_DATA


def permission_denied(request):
    raise PermissionDenied


handler403 = "backend.apps.error_pages.views.permission_denied"
handler404 = "backend.apps.error_pages.views.page_not_found"
handler500 = "backend.apps.error_pages.views.server_error"

urlpatterns = [
    path("403/", permission_denied),
    path("500/", server_error),
    path("", include("backend.apps.error_pages.urls", namespace="error")),
]


@override_settings(
    DEBUG=False,
    SITE_ID=100,
    ROOT_URLCONF=__name__,
)
class CustomErrorTestCase(TestCase):
    request_factory = RequestFactory()

    def test_permission_denied(self):
        response = self.client.get("/403/")
        self.assertContains(response, "Access denied", status_code=403)

    def test_page_not_found(self):
        response = self.client.get("/fake/")
        self.assertContains(response, "Page not found", status_code=404)

    def test_server_error(self):
        response = self.client.get("/500/")
        self.assertContains(response, "Something went wrong", status_code=500)

    def test_bad_request(self):
        request = self.request_factory.get("/400.html")
        response = bad_request(request, Exception())
        self.assertContains(response, "Bad request", status_code=400)

    @override_settings(CSRF_FAILURE_VIEW="backend.apps.error_pages.views.csrf_failure")
    def test_csrf_failure(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/405.html")
        self.assertContains(response, "Access denied", status_code=403)

    def test_error_page(self, status=500, title=None, message=None):
        data = ERROR_DATA.get(status, {})
        title = title or data.get("title")
        message = message or data.get("message")
        response = self.client.get("/%s.html" % status)
        self.assertContains(response, str(status), status_code=status)
        self.assertIn(force_bytes(str(title)), response.content)
        self.assertIn(force_bytes(str(message)), response.content)

    @override_settings(SITE_ID=1)
    def test_error_page_with_site(self):
        self.test_error_page()

    @override_settings(
        STATIC_URL="/static/",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "loaders": [
                        (
                            "django.template.loaders.locmem.Loader",
                            {
                                "error.html": "This is a custom template. {{ STATIC_URL }}"
                            },
                        ),
                    ],
                },
            }
        ],
    )
    def test_error_page_custom_template(self):
        response = self.client.get("/404.html")
        self.assertContains(
            response, "This is a custom template. /static/", status_code=404
        )

    def test_error_page_non_existent_template(self):
        request = self.request_factory.get("/502.html")
        args = [request, 502, "nonexistent"]
        self.assertRaises(TemplateDoesNotExist, error_page, *args)

    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "loaders": [
                        ("django.template.loaders.locmem.Loader", {}),
                    ],
                },
            }
        ]
    )
    def test_error_page_template_not_found(self):
        response = self.client.get("/502.html")
        self.assertContains(response, "<h1>Error 502</h1>", status_code=502)
