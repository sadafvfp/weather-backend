from django.urls import path
from . import views

DEVICES = [
    ("sapa", views.SAPAViewSet),
    ("ospm", views.OSPMViewSet),
    ("esps", views.ESPSViewSet),
]


urlpatterns = []

for name, viewset in DEVICES:
    urlpatterns.extend(
        [
            path(
                f"{name}/<int:device_id>/",
                viewset.as_view(
                    {
                        "get": "list",
                        "post": "create",
                    }
                ),
                name=f"{name}-list",
            ),
            path(
                f"{name}/<int:device_id>/<str:created_datetime>/",
                viewset.as_view(
                    {
                        "get": "retrieve",
                        "put": "update",
                        "delete": "destroy",
                    }
                ),
                name=f"{name}-detail",
            ),
        ]
    )
