from datetime import timedelta
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.utils import timezone
from backend.apps.custom.serializers.fields import (
    RoundedFloatField,
    to_persian_string,
)

from .base import TemperatureSerializer, AirDataSerializer
from .history import QueryParamSerializer as HistoryQueryParamSerializer


class PublicAirSerializer(AirDataSerializer, TemperatureSerializer):

    persian_datetime = serializers.SerializerMethodField(label="تاریخ و زمان")

    @cached_property
    def _tz(self):
        return timezone.get_current_timezone()

    def _bucket(self, obj):
        view = self.context.get("view")
        time_add = getattr(view, "time_add", timedelta())
        return obj["bucket"] + time_add

    def get_persian_datetime(self, obj):
        return to_persian_string(self._bucket(obj), self._tz)


class PublicTemperatureSerializer(TemperatureSerializer):
    persian_datetime = serializers.SerializerMethodField(label="تاریخ و زمان")

    @cached_property
    def _tz(self):
        return timezone.get_current_timezone()

    def _bucket(self, obj):
        view = self.context.get("view")
        time_add = getattr(view, "time_add", timedelta())
        return obj["bucket"] + time_add

    def get_persian_datetime(self, obj):
        return to_persian_string(self._bucket(obj), self._tz)


class QueryParamSerializer(HistoryQueryParamSerializer):
    fields = serializers.CharField()
