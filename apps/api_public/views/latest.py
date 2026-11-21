from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from backend.apps.device.models import (
    LatestData,
    Granularity,
    DataStatus,
    DeviceStatus,
)

from ..serializers.latest import AirLatestSerializer


class LatestDataByCategoryView(ListAPIView):
    category = None  # set via as_view(category="air")
    granularity = Granularity.THREE_MINUTE  # default; overridable by query param

    # authentication_classes = []
    permission_classes = [IsAuthenticated]

    def get_granularity(self):
        raw = self.request.query_params.get("granularity")
        if raw is not None and raw.isdigit() and int(raw) in Granularity.values:
            return int(raw)
        return self.granularity

    def get_status(self):
        status = int(self.request.GET.get("status"))
        return status

    def get_queryset(self):
        return LatestData.objects.filter(
            granularity=self.get_granularity(),
            status=self.get_status(),
            deviceinfo__status=DeviceStatus.PRODUCTION,
        ).select_related("deviceinfo")


class AirListAPIView(LatestDataByCategoryView):
    category = "air"
    serializer_class = AirLatestSerializer
