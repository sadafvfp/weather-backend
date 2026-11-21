from rest_framework import serializers

from backend.apps.device.models import LatestData
from backend.apps.custom.serializers.fields import PersianDateTimeField

from .base import DeviceSerializer, AirDataSerializer


class LatestBaseSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(source="deviceinfo")
    created_datetime = PersianDateTimeField()

    class Meta:
        model = LatestData
        fields = ["data", "device", "created_datetime", "status"]


class AirLatestSerializer(LatestBaseSerializer):
    data = AirDataSerializer()
