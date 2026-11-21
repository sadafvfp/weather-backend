from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .AQICalculator import AQICalculator

# class AQISerializer(serializers.Serializer):
#     pm10_aqi = serializers.SerializerMethodField(required=False)
#     pm25_aqi = serializers.SerializerMethodField(required=False)
#     so2_aqi = serializers.SerializerMethodField(required=False)
#     no2_aqi = serializers.SerializerMethodField(required=False)
#     o3_aqi = serializers.SerializerMethodField(required=False)
#     co_aqi = serializers.SerializerMethodField(required=False)
#     aqi = serializers.SerializerMethodField(required=False)
#     main_pollutant = serializers.SerializerMethodField(required=False)

#     AQI_FIELDS = {
#         "pm10": ("PM10", AQICalculator.PM10),
#         "pm25": ("PM2.5", AQICalculator.PM25),
#         "so2": ("SO2", AQICalculator.SO2),
#         "no2": ("NO2", AQICalculator.NO2),
#         "o3": ("O3", AQICalculator.O3),
#         "co": ("CO", AQICalculator.CO),
#     }

#     def _get_value(self, obj, field):
#         if isinstance(obj, dict):
#             return obj.get(field)
#         return getattr(obj, field, None)

#     def _calculate_aqi(self, obj, field):
#         value = self._get_value(obj, field)

#         if value is None:
#             return None

#         _, calculator = self.AQI_FIELDS[field]
#         return int(calculator(value))

#     def get_pm10_aqi(self, obj):
#         return self._calculate_aqi(obj, "pm10")

#     def get_pm25_aqi(self, obj):
#         return self._calculate_aqi(obj, "pm25")

#     def get_so2_aqi(self, obj):
#         return self._calculate_aqi(obj, "so2")

#     def get_no2_aqi(self, obj):
#         return self._calculate_aqi(obj, "no2")

#     def get_o3_aqi(self, obj):
#         return self._calculate_aqi(obj, "o3")

#     def get_co_aqi(self, obj):
#         return self._calculate_aqi(obj, "co")

#     def _max_aqi(self, obj):
#         values = [
#             (self._calculate_aqi(obj, field), pollutant)
#             for field, (pollutant, _) in self.AQI_FIELDS.items()
#         ]

#         values = [v for v in values if v[0] is not None]

#         if not values:
#             return None, None

#         return max(values, key=lambda x: x[0])

#     def get_aqi(self, obj):
#         aqi, _ = self._max_aqi(obj)
#         return aqi

#     def get_main_pollutant(self, obj):
#         _, pollutant = self._max_aqi(obj)
#         return pollutant

#     def _has_field(self, obj, field):
#         if isinstance(obj, dict):
#             return field in obj
#         return hasattr(obj, field)

#     def to_representation(self, instance):
#         data = super().to_representation(instance)

#         for field in self.AQI_FIELDS:
#             if not self._has_field(instance, field):
#                 data.pop(f"{field}_aqi", None)

#         return data


class AQISerializer(serializers.Serializer):
    AQI_FIELDS = {
        "pm10": ("PM10", AQICalculator.PM10),
        "pm25": ("PM2.5", AQICalculator.PM25),
        "so2": ("SO2", AQICalculator.SO2),
        "no2": ("NO2", AQICalculator.NO2),
        "o3": ("O3", AQICalculator.O3),
        "co": ("CO", AQICalculator.CO),
    }

    def _has_field(self, obj, field):
        if isinstance(obj, dict):
            return field in obj
        return hasattr(obj, field)

    def _get_value(self, obj, field):
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        valid = {}  # pollutant name -> aqi
        for field, (name, calculator) in self.AQI_FIELDS.items():
            if not self._has_field(instance, field):
                continue
            value = self._get_value(instance, field)
            aqi = None if value is None else int(calculator(value))
            data[f"{field}_aqi"] = aqi
            if aqi is not None:
                valid[name] = aqi

        if valid:
            main = max(valid, key=valid.get)
            data["aqi"], data["main_pollutant"] = valid[main], main
        else:
            data["aqi"] = data["main_pollutant"] = None

        return data


class AQISerializer1(serializers.Serializer):
    AQI_FIELDS = {
        "pm10": ("PM10", AQICalculator.PM10),
        "pm25": ("PM2.5", AQICalculator.PM25),
    }

    def _aqi_data(self, obj):
        """Returns {'pm10_aqi': ..., ..., 'aqi': ..., 'main_pollutant': ...}."""
        out, valid = {}, {}
        for field, (name, calculator) in self.AQI_FIELDS.items():
            if field not in obj:  # rows are dicts
                continue
            value = obj[field]
            aqi = None if value is None else int(calculator(value))
            out[f"{field}_aqi"] = aqi
            if aqi is not None:
                valid[name] = aqi
        if not out:  # no pollutant keys in this row -> pop everything
            return {}

        if valid:
            main = max(valid, key=valid.get)
            out["aqi"], out["main_pollutant"] = valid[main], main
        else:
            out["aqi"] = out["main_pollutant"] = None
        return out

    def get_fields(self):
        fields = super().get_fields()
        for key, (name, _calc) in self.AQI_FIELDS.items():
            fields[f"{key}_aqi"] = serializers.IntegerField(
                read_only=True,
                required=False,
                label=_("%(name)s AQI") % {"name": name},
            )
        fields["aqi"] = serializers.IntegerField(
            read_only=True, required=False, label=_("AQI")
        )
        fields["main_pollutant"] = serializers.CharField(
            read_only=True, required=False, label=_("آلاینده عامل")
        )
        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(self._aqi_data(instance))
        return data
