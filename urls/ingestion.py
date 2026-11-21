from django.urls import path, include
# from ..views import RobotsBlockView

# handler403 = "backend.apps.error_pages.views.permission_denied"
# handler404 = "backend.apps.error_pages.views.page_not_found"
# handler500 = "backend.apps.error_pages.views.server_error"


urlpatterns = [
    path("aqs/", include("backend.apps.api_ingestion.urls")),
    # path("robots.txt", RobotsBlockView.as_view(), name="robots"),
]
