from rest_framework.viewsets import ModelViewSet, GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend
from device.filters import BaseDeviceFilter
from django.db.models import Avg
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.renderers import BrowsableAPIRenderer
from datetime import timedelta


from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer

from export.mixins import ExcelModelMixin
from device.permissions import DeviceIsActive
from device.services import InfoService

from mytimescale.aggregates import Interpolate
from .serializers import QueryParamSerializer


class BaseDeviceViewSet(ModelViewSet):
    permission_classes = [DeviceIsActive]
    authentication_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = BaseDeviceFilter
    model = None
    interval = None
    lookup_field = "created_datetime"

    def get_queryset(self):
        return self.queryset.filter(device_id=self.kwargs["device_id"])

    def perform_create(self, serializer):
        serializer.save(device_id=self.kwargs["device_id"])

    def get_device_info(self):
        return InfoService.get_device_info(self.device_type, self.kwargs["device_id"])
