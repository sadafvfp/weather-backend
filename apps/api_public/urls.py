from django.urls import path
from rest_framework.routers import SimpleRouter
from .views.latest import AirListAPIView
from .views.history import (
    AirHistoryOnlineListAPIView,
    AirHistoryHourlyListAPIView,
    AirHistoryDailyListAPIView,
    AirHistoryDailyTemperatureListAPIView,
)
from .views.excel import (
    AirExcelOnlineListAPIView,
    AirExcelHourlyAPIView,
    AirExcelDailyAPIView,
    AirExcelTemperatureAPIView,
)
from .views.station import StationListAPIView
from .views.info import DeviceInfoModelViewSet
from .views.ospm_admin import OSPMThreeMinuteDeleteAPIView

router = SimpleRouter()
router.register("device-info", DeviceInfoModelViewSet, "device-info")

urlpatterns = [
    path("air/", AirListAPIView.as_view()),
    path(
        "history/online/<str:slug>/",
        AirHistoryOnlineListAPIView.as_view(),
    ),
    path(
        "history/hourly/<str:slug>/",
        AirHistoryHourlyListAPIView.as_view(),
    ),
    path(
        "history/daily/<str:slug>/",
        AirHistoryDailyListAPIView.as_view(),
    ),
    path(
        "history/daily-temp/<str:slug>/",
        AirHistoryDailyTemperatureListAPIView.as_view(),
    ),
    path(
        "excel/online/<str:slug>/",
        AirExcelOnlineListAPIView.as_view(),
    ),
    path(
        "excel/hourly/<str:slug>/",
        AirExcelHourlyAPIView.as_view(),
    ),
    path(
        "excel/daily/<str:slug>/",
        AirExcelDailyAPIView.as_view(),
    ),
    path(
        "excel/daily-temp/<str:slug>/",
        AirExcelTemperatureAPIView.as_view(),
    ),
    path("station/<str:slug>/", StationListAPIView.as_view()),
    path(
        "admin/ospm/<int:device_id>/three-minute/delete/",
        OSPMThreeMinuteDeleteAPIView.as_view(),
        name="ospm-three-minute-delete",
    ),
]
urlpatterns += router.urls
