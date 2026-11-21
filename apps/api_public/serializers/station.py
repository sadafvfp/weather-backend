from rest_framework import serializers

from .base import AirDataSerializer
from backend.apps.device.models import LatestData
from backend.apps.custom.serializers.fields import PersianDateTimeField


class StationSerializer(serializers.ModelSerializer):
    data = AirDataSerializer()
    created_datetime = PersianDateTimeField()

    class Meta:
        model = LatestData
        fields = ["data", "created_datetime", "granularity"]
