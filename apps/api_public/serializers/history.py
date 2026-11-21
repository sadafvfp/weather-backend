from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from backend.apps.custom.serializers.fields import (
    PersianDateTimeField,
    RoundedDateTimeField,
    RoundedFloatField,
    to_persian_string,
)
from datetime import timedelta
from django.utils.functional import cached_property
from django.utils import timezone
from backend.apps.aqi.serializers import AQISerializer, AQISerializer1
from backend.apps.device.sensor_codes import sensor_error_code_label


class QueryParamSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        view = self.context["view"]
        max_range = getattr(view, "max_date_range", None)
        time_add = getattr(view, "time_add", timedelta(0))
        start, end = attrs["start_date"], attrs["end_date"]

        if end <= start:
            raise ValidationError(
                {
                    "detail": "end date must be greater than start date",
                },
            )
        if max_range and end - start > max_range:
            raise serializers.ValidationError(
                {"detail": f"Date range cannot exceed {max_range.days} days."}
            )
        attrs["start_date"] = start - time_add
        attrs["end_date"] = end - time_add

        return attrs

    def to_internal_value(self, data):

        return super().to_internal_value(data)


class PublicAirSerializer1(AQISerializer1):
    FLOAT_FIELDS = (
        "pm10",
        "pm10_min",
        "pm10_max",
        "pm25",
        "pm25_min",
        "pm25_max",
        "temperature",
        "temperature_min",
        "temperature_max",
        "humidity",
        "flow",
    )

    @cached_property
    def _tz(self):
        return timezone.get_current_timezone()

    def _bucket(self, obj):
        view = self.context.get("view")
        time_add = getattr(view, "time_add", timedelta())
        return obj["bucket"] + time_add

    def _iso(self, dt):
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, self._tz)
        else:
            dt = dt.astimezone(self._tz)
        s = dt.isoformat()
        return s[:-6] + "Z" if s.endswith("+00:00") else s

    def to_representation(self, obj):
        data = {
            "created_datetime": self._iso(obj["bucket"]),  # same as before: no time_add
            "persian_datetime": to_persian_string(self._bucket(obj), self._tz),
        }
        for name in self.FLOAT_FIELDS:
            if name in obj:
                v = obj[name]
                data[name] = None if v is None else round(float(v), 2)
        if "error_code" in obj:
            data["error_code"] = obj["error_code"]
            data["error_code_label"] = sensor_error_code_label(obj.get("error_code"))
        if "has_record" in obj:
            data["has_record"] = bool(obj["has_record"])
        data.update(self._aqi_data(obj))
        return data
