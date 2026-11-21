from django.urls import path, include
from django.conf import settings


from . import urlpatterns
from ..views import csrf

from rest_framework import permissions
# from drf_yasg.views import get_schema_view
# from drf_yasg import openapi
from backend.apps.accounts.views import CustomLoginView
from dj_rest_auth.views import LogoutView

...

# schema_view = get_schema_view(
#     openapi.Info(
#         title="Snippets API",
#         default_version="v1",
#         description="Test description",
#         terms_of_service="https://www.google.com/policies/terms/",
#         contact=openapi.Contact(email="contact@snippets.local"),
#         license=openapi.License(name="BSD License"),
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
# )
urlpatterns += [
    path("kwz/", include("backend.apps.api_public.urls")),
    path("auth/login/", CustomLoginView.as_view(), name="rest_login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/", include("backend.apps.accounts.urls")),
    # path("robots.txt", RobotsBlockView.as_view(), name="robots"),
    path("api/csrf/", csrf, name="csrf"),
]
# if settings.DEBUG:
#     urlpatterns += [
#         path(
#             "swagger<format>/",
#             schema_view.without_ui(cache_timeout=0),
#             name="schema-json",
#         ),
#         path(
#             "swagger/",
#             schema_view.with_ui("swagger", cache_timeout=0),
#             name="schema-swagger-ui",
#         ),
#     ]
