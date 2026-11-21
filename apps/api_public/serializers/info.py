from datetime import timedelta

import nh3
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from backend.apps.device.models import DeviceInfo
from backend.apps.custom.serializers.fields import PersianDateTimeField


class DeviceInfoSerializer(serializers.ModelSerializer):
    device_id = serializers.IntegerField(
        validators=[
            UniqueValidator(
                queryset=DeviceInfo.objects.all(),
                message=_("ایستگاه با این شناسه از قبل موجود می‌باشد."),
            )
        ]
    )
    created_at = PersianDateTimeField(interval=timedelta(minutes=1), read_only=True)
    updated_at = PersianDateTimeField(interval=timedelta(minutes=1), read_only=True)

    class Meta:
        model = DeviceInfo
        fields = [
            "status",
            "created_at",
            "updated_at",
            "province",
            "city",
            "station_name",
            "slug",
            "device_id",
        ]
        read_only_fields = [
            "slug",
            "created_at",
            "updated_at",
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=DeviceInfo.objects.all(),
                fields=["province", "city", "station_name"],
                message=_(
                    "ایستگاهی با این استان، شهر و نام ایستگاه قبلا ثبت شده است."
                ),
            )
        ]

    def _reject_html(self, value):
        value = value.strip()
        if nh3.clean(value, tags=set()) != value:
            raise serializers.ValidationError("HTML is not allowed.")
        return value

    def validate_device_id(self, value):
        if self.instance is not None and value != self.instance.device_id:
            raise serializers.ValidationError(
                _("تغییر شناسه دستگاه پس از ثبت مجاز نیست.")
            )
        return value

    def validate_station_name(self, value):
        return self._reject_html(value)

    def validate_province(self, value):
        return self._reject_html(value)

    def validate_city(self, value):
        return self._reject_html(value)

    @staticmethod
    def _raise_django_validation_error(exc):
        if getattr(exc, "message_dict", None):
            raise serializers.ValidationError(exc.message_dict)
        raise serializers.ValidationError(list(exc.messages))

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            self._raise_django_validation_error(exc)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            self._raise_django_validation_error(exc)
