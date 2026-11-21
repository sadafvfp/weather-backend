from django.urls import path, include
import os

if int(os.environ.get("DASHBOARD")):
    urlpatterns = [
        path("", include("device.panel.urls")),
        path("public/", include("device.public.urls")),
    ]
else:
    urlpatterns = [
        path("", include("device.public.urls")),
    ]
