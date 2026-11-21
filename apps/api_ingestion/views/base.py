from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework import mixins
from rest_framework.response import Response
from datetime import timedelta
from functools import cached_property


from ...device.permissions import DeviceIsActive
from ...device.services import InfoService, IngestionService
from ...device.tasks import history_data_store


class BaseInsertDataAPIView(mixins.CreateModelMixin, GenericAPIView):
    serializer_class = None
    permission_classes = [DeviceIsActive]
    authentication_classes = []
    min_gap_map = {}
    sensor_threshold = {}
    map_dict = {}

    @cached_property
    def normalized_data(self):
        raw = (
            self.request.query_params
            if self.request.method == "GET"
            else self.request.data
        )
        return self.normalize_payload(raw)

    def get_device_id(self):
        device_id = self.normalized_data.get("device_id")
        if isinstance(device_id, (list, tuple)):
            device_id = device_id[0] if device_id else None
        if device_id in (None, ""):
            raise ValidationError({"device_id": "This query parameter is required."})
        try:
            return int(device_id)
        except (TypeError, ValueError):
            raise ValidationError({"device_id": "Must be a valid integer."})

    @cached_property
    def device_info(self):
        return InfoService.get_device(self.get_device_id())

    def normalize_payload(self, payload):
        payload = dict(payload)
        # Avoid mutating QueryDict / caller's dict in place.
        for key, value in payload.items():
            if isinstance(value, (list, tuple)) and len(value) == 1:
                payload[key] = value[0]
        for key, mapped_key in self.map_dict.items():
            if key in payload:
                payload[mapped_key] = payload.pop(key)
        return payload

    def get(self, request, *args, **kwargs):
        return self._insert(self.normalized_data)

    def post(self, request, *args, **kwargs):
        return self._insert(self.normalized_data)

    def _insert(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        device_info = self.device_info
        validated_data = IngestionService.prepare_reading(
            device_info,
            serializer.validated_data,
            min_gap_map=self.min_gap_map,
            sensor_threshold=self.sensor_threshold,
        )

        celery_payload = {
            **validated_data,
            "created_datetime": validated_data["created_datetime"].isoformat(),
        }

        history_data_store.delay(celery_payload)

        return Response("Done", status=status.HTTP_200_OK)
