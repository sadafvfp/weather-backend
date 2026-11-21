from django.urls import path

from .views import OSPMAPIView, OSPMBatchAPIView

urlpatterns = [
    path("OSPM/", OSPMAPIView.as_view()),
    path("OSPM/batch/", OSPMBatchAPIView.as_view()),
]
