from rest_framework.generics import ListAPIView
from functools import cached_property
from rest_framework.permissions import IsAuthenticated

from backend.apps.device.models import LatestData, DataStatus
from backend.apps.device.services import InfoService
from backend.apps.device.permissions import DeviceIsActive, HasDeviceAccess
from ..serializers.station import StationSerializer


class StationListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    # permission_classes = [DeviceIsActive]
    serializer_class = StationSerializer
    pagination_class = None

    @cached_property
    def device_info(self):
        slug = self.kwargs["slug"]
        return InfoService.get_device_by_slug(slug)

    def get_queryset(self):

        return LatestData.objects.filter(
            status=DataStatus.PRODUCTION, deviceinfo_id=self.device_info.device_id
        )
