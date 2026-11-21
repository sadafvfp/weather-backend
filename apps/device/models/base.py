from django.db import models
from django.utils.translation import gettext_lazy as _

# from timescale.db.models.managers import TimescaleManager
from backend.apps.mytimescale.managers import MyTimescaleManager

from ...accounts.models import User


class DataStatus(models.IntegerChoices):
    PRODUCTION = 0, _("Production")
    TEST = 1, _("Test")
    SUSPICIOUS = 2, _("Suspicious")


class BaseTimeSeriesModel(models.Model):
    created_datetime = models.DateTimeField(_("Created Datetime"))

    device_id = models.PositiveIntegerField(_("Device ID"))
    objects = models.Manager()
    timescale = MyTimescaleManager()

    class Meta:
        abstract = True


class TemperatureSensor(models.Model):
    humidity = models.FloatField(_("Humidity"))
    temperature = models.FloatField(_("Temperature"))

    class Meta:
        abstract = True


class TemperatureSensorHourly(models.Model):
    humidity = models.FloatField(_("Humidity"))
    temperature_min = models.FloatField(_("Temperature_min"))
    temperature_max = models.FloatField(_("Temperature_max"))

    class Meta:
        abstract = True


class DeviceStatus(models.IntegerChoices):
    PRODUCTION = 0, "Production"
    TEST = 1, "Test"
    DEACTIVATED = 2, "Deactivated"


class BaseDeviceInfo(models.Model):
    status = models.PositiveSmallIntegerField(
        choices=DeviceStatus, default=DeviceStatus.TEST
    )
    user = models.ManyToManyField(User, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True
