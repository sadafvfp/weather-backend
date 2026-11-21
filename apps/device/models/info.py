from django.db import models, IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from .base import DataStatus, BaseDeviceInfo, DeviceStatus


class DeviceInfo(BaseDeviceInfo):
    device_id = models.IntegerField(_("Device ID"), unique=True)
    province = models.CharField(_("Province"), max_length=100, null=False, blank=True)
    city = models.CharField(_("City"), max_length=100, null=False, blank=True)
    station_name = models.CharField(
        _("Station Name"), max_length=150, null=False, blank=True
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=True,  # required for Persian
        blank=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["province", "city", "station_name"],
                name="unique_province_city_station_name",
            )
        ]
        db_table = "device_info"
        verbose_name = "Device Info"
        verbose_name_plural = "Device Info"

    def _build_slug(self):
            parts = [
                self.province,
                self.city,
                self.station_name,
            ]
            if not all(parts):
                raise ValidationError(
                    "Production devices need station name, city and province."
                )
            return slugify(" ".join(parts), allow_unicode=True)
    

    def clean(self):
        if self.pk:
            original_id = (
                DeviceInfo.objects.filter(pk=self.pk)
                .values_list("device_id", flat=True)
                .first()
            )
            if original_id is not None and original_id != self.device_id:
                raise ValidationError(
                    {"device_id": _("Changing device_id is not allowed once created.")}
                )
        self.slug = (
            self._build_slug()
        )  # raises ValidationError for incomplete production devices

    def save(self, *args, **kwargs):
        if self.pk:
            original_id = (
                DeviceInfo.objects.filter(pk=self.pk)
                .values_list("device_id", flat=True)
                .first()
            )
            if original_id is not None and original_id != self.device_id:
                raise ValidationError(
                    {"device_id": _("Changing device_id is not allowed once created.")}
                )
        self.slug = self._build_slug()
        super().save(*args, **kwargs)
     

    def __str__(self):
        device_id = self.device_id
        return "Device " + str(device_id)


class Granularity(models.IntegerChoices):
    THREE_MINUTE = 0, _("Online")
    HOURLY = 1, _("Hourly")
    DAILY = 2, _("Daily")
    DAILY_TEMPERATURE = 20, _("Daily Temperature")


class LatestData(models.Model):
    created_datetime = models.DateTimeField(null=True)
    deviceinfo = models.ForeignKey(
        DeviceInfo, on_delete=models.CASCADE, related_name="+", to_field="device_id"
    )
    status = models.PositiveSmallIntegerField(choices=DataStatus.choices)
    granularity = models.PositiveSmallIntegerField(
        _("Granularity"), choices=Granularity.choices
    )

    data = models.JSONField()

    class Meta:
        db_table = "device_latest"
        verbose_name = "Device Latest Data"
        verbose_name_plural = "Device Latest Data"
        constraints = [
            models.UniqueConstraint(
                fields=["deviceinfo", "status", "granularity"],
                name="unique_latest_deviceinfo",
            )
        ]
