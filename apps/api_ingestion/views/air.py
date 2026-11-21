from functools import cached_property
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from ...device.models import OSPM
from ...device.permissions import DeviceIsActive
from ...device.services import HistoryDataService, InfoService
from ..serializers import OSPMBatchIngestionSerializer, OSPMSerializer
from .base import BaseInsertDataAPIView


class OSPMAPIView(BaseInsertDataAPIView):
    device_type = "OSPM"
    queryset = OSPM.objects.all()
    serializer_class = OSPMSerializer
    map_dict = {"name": "device_id"}


class OSPMBatchAPIView(GenericAPIView):
    """
    Synchronous batch ingestion endpoint for historical/buffered OSPM uploads.
    Accepts:
    {
        "device_id": 110,
        "total_batch": 5,
        "batch_id": 1,
        "data_h": [{"created_datetime": "...", "pm10": ..., "pm25": ..., "temperature": ..., "humidity": ..., "flow": ..., "error_code": 0}],
        "data_s": [{"created_datetime": "...", "pm10": ..., "pm25": ..., "temperature": ..., "humidity": ..., "flow": ..., "error_code": 4}]
    }
    """

    serializer_class = OSPMBatchIngestionSerializer
    permission_classes = [DeviceIsActive]
    authentication_classes = []

    def get_device_id(self):
        if not isinstance(self.request.data, dict):
            raise ValidationError({"detail": "Invalid JSON object payload."})
        device_id = self.request.data.get("device_id")
        if device_id in (None, "") or isinstance(device_id, bool):
            raise ValidationError({"device_id": "This field is required."})
        try:
            return int(device_id)
        except (TypeError, ValueError):
            raise ValidationError({"device_id": "Must be a valid integer."})

    @cached_property
    def device_info(self):
        return InfoService.get_device(self.get_device_id())

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = HistoryDataService.process_batch(
            device_info=self.device_info,
            validated_payload=serializer.validated_data,
        )
        return Response(result, status=status.HTTP_200_OK)
