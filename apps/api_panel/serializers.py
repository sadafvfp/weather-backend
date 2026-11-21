from ..device.models import SAPA, OSPM, ESPS

from rest_framework import serializers
from custom.serializers.fields import (
    PersianDateTimeField,
    RoundedDateTimeField,
    RoundedFloatField,
)
from datetime import timedelta
from django.utils import timezone
from aqi.serializers import AQISerializer
from custom.serializers.fields import QueryParamDateTimeField


class BaseSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    persian_datetime = PersianDateTimeField(source="created_datetime", read_only=True)
    created_datetime = RoundedDateTimeField(format="%Y-%m-%d %H:%M:%S")

    def get_url(self, obj):
        request = self.context["request"]
        view = self.context["view"]
        device_type = view.device_type.lower()
        device_id = view.kwargs.get("device_id")
        created_datetime = obj.created_datetime
        return request.build_absolute_uri(
            f"/device/{device_type}/{device_id}/{created_datetime:%Y-%m-%d %H:%M:%S}/"
        )

    def update(self, instance, validated_data):
        validated_data.pop("created_datetime", None)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        view = self.context.get("view")
        if getattr(view, "action", None) != "list":
            rep.pop("url", None)
        return rep


class BaseAirSerializer(BaseSerializer, AQISerializer):
    temperature = RoundedFloatField(required=False)
    humidity = RoundedFloatField(required=False)
    common_fields = [
        "created_datetime",
        "persian_datetime",
        "pm10",
        "pm25",
        "temperature",
        "humidity",
        "pm10_aqi",
        "pm25_aqi",
        "aqi",
        "main_pollutant",
        "url",
    ]


class SAPASerializer(BaseAirSerializer):
    class Meta:
        model = SAPA
        fields = BaseAirSerializer.common_fields + [
            "so2",
            "no2",
            "o3",
            "co",
            "so2_aqi",
            "no2_aqi",
            "o3_aqi",
            "co_aqi",
        ]


class OSPMSerializer(BaseAirSerializer):
    class Meta:
        model = OSPM
        fields = BaseAirSerializer.common_fields


class ESPSSerializer(BaseAirSerializer):
    class Meta:
        model = ESPS
        fields = BaseAirSerializer.common_fields
