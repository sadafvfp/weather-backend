from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


from backend.apps.aqi.serializers import AQISerializer1
from backend.apps.custom.serializers.fields import RoundedFloatField
from backend.apps.device.models import DeviceInfo
from backend.apps.device.sensor_codes import sensor_error_code_label


class TemperatureSerializer(serializers.Serializer):
    temperature = RoundedFloatField(required=False, label="دما")
    temperature_min = RoundedFloatField(required=False, label="دما کمینه")
    temperature_max = RoundedFloatField(required=False, label="دما بیشینه")
    humidity = RoundedFloatField(required=False, label="رطوبت نسبی")


class AirDataSerializer(AQISerializer1, TemperatureSerializer):
    pm10 = RoundedFloatField(required=False, label="PM10")
    pm10_min = RoundedFloatField(required=False, label="PM10 کمینه")
    pm10_max = RoundedFloatField(required=False, label="PM10 بیشینه")
    pm25 = RoundedFloatField(required=False, label="PM2.5")
    pm25_min = RoundedFloatField(required=False, label="PM2.5 کمینه")
    pm25_max = RoundedFloatField(required=False, label="PM2.5 بیشینه")
    flow = RoundedFloatField(required=False, allow_null=True, label="جریان")
    error_code = serializers.IntegerField(required=False, allow_null=True, label="کد ارور")
    error_code_label = serializers.SerializerMethodField(label="ارور")

    def get_error_code_label(self, obj):
        if isinstance(obj, dict):
            code = obj.get("error_code")
        else:
            code = getattr(obj, "error_code", None)
        return sensor_error_code_label(code)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInfo
        fields = [
            "device_id",
            "province",
            "city",
            "station_name",
            "slug",
        ]
