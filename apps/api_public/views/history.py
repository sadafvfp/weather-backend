from datetime import timedelta
from functools import cached_property
from functools import lru_cache
from rest_framework.generics import ListAPIView
from django.apps import apps
from django.db import models

from backend.apps.device.permissions import (
    DeviceIsActive,
    HasDeviceAccess,
    DeviceExists,
)
from rest_framework.permissions import IsAuthenticated
from backend.apps.device.services import InfoService
from backend.apps.custom.pagination import LargeResultsSetPagination
from backend.apps.device.filters import BucketOrderingFilter
from backend.apps.device.models import (
    DataStatus,
    OSPM,
    OSPMHourly,
    OSPMDaily,
    OSPMDailyTemperature,
)
from ..serializers.history import QueryParamSerializer, PublicAirSerializer1

NUMERIC = (models.FloatField, models.IntegerField, models.DecimalField)


@lru_cache(maxsize=None)
def get_model_field_info(model, ignore_fields):
    """ignore_fields must be a frozenset so it's hashable."""
    fields = model._meta.fields
    names = {f.name for f in fields}
    measurements = (
        frozenset(f.name for f in fields if isinstance(f, NUMERIC)) - ignore_fields
    )
    return names, measurements


class PublicBaseAirDeviceListAPIView(ListAPIView):
    ignore_fields = {
        "id",
        "pk",
        "created_datetime",
        "device_id",
        "status",
        "error_code"
    }
    permission_classes = [IsAuthenticated, DeviceExists]
    pagination_class = LargeResultsSetPagination
    # permission_classes = [DeviceIsActive, HasDeviceAccess]
    # authentication_classes = []
    model = None
    interval = None
    status = None
    datetime_field = "created_datetime"
    model_name_granularity = ""
    filter_backends = [BucketOrderingFilter]
    serializer_queryparams = QueryParamSerializer

    def get_status(self):
        return self.status

    @cached_property
    def device_info(self):
        slug = self.kwargs["slug"]
        return InfoService.get_device_by_slug(slug)

    @cached_property
    def get_model(self):
        if self.model:
            return self.model
        device_type = self.device_info.device_type_id
        return apps.get_model("device", f"{device_type}{self.model_name_granularity}")

    @cached_property
    def _field_info(self):
        return get_model_field_info(self.get_model, frozenset(self.ignore_fields))

    @cached_property
    def measurement_fields(self):
        return self._field_info[1]

    def get_query_params(self):
        query_params = self.serializer_queryparams(
            data=self.request.query_params, context={"view": self}
        )
        query_params.is_valid(raise_exception=True)
        return query_params.validated_data

    def get_queryset(self):
        filters = self.get_query_params()
        names, _ = self._field_info

        qs = self.get_model.timescale.time_bucket_gapfill(
            self.datetime_field,
            self.interval,
            start=filters["start_date"],
            end=filters["end_date"],
            timezone="Asia/Tehran",
        ).filter(
            device_id=self.device_info.device_id,
            created_datetime__range=[filters["start_date"], filters["end_date"]],
        )

        if "status" in names:
            qs = qs.filter(
                status=self.get_status(),
                created_datetime__range=[filters["start_date"], filters["end_date"]],
            )

        annotations = {}
        for f in self.measurement_fields:
            if f.endswith("_min"):
                annotations[f] = models.Min(f)
            elif f.endswith("_max"):
                annotations[f] = models.Max(f)
            else:
                annotations[f] = models.Avg(f)
        return qs.annotate(**annotations)


class AirHistoryOnlineListAPIView(PublicBaseAirDeviceListAPIView):
    interval = "3 minutes"
    model = OSPM
    serializer_class = PublicAirSerializer1
    max_date_range = timedelta(days=18)

    def get_status(self):
        status = int(self.request.GET.get("status"))
        return status

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(
            has_record=models.Count("device_id"),
            error_code=models.Max("error_code"),
        )


class AirHistoryHourlyListAPIView(PublicBaseAirDeviceListAPIView):
    interval = "1 hour"
    time_add = timedelta(hours=1)
    serializer_class = PublicAirSerializer1
    model = OSPMHourly
    max_date_range = timedelta(days=366)


class AirHistoryDailyListAPIView(PublicBaseAirDeviceListAPIView):
    interval = "1 day"
    time_add = timedelta(days=1, hours=11)
    serializer_class = PublicAirSerializer1
    model = OSPMDaily
    max_date_range = timedelta(days=22 * 366)


class AirHistoryDailyTemperatureListAPIView(PublicBaseAirDeviceListAPIView):
    interval = "1 day"
    model = OSPMDailyTemperature
    serializer_class = PublicAirSerializer1
    max_date_range = timedelta(days=22 * 366)
