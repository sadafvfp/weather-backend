from django.db import models
from django.utils.translation import gettext_lazy as _
from backend.apps.mytimescale.managers import MyTimescaleManager
from .base import (
    BaseTimeSeriesModel,
    TemperatureSensor,
    TemperatureSensorHourly,
    DataStatus,
)


class ParticleSensorModel(BaseTimeSeriesModel):
    pm10 = models.FloatField(_("PM10"))
    pm25 = models.FloatField(_("PM2.5"))

    class Meta:
        abstract = True


class ParticleSensorHourlyModel(ParticleSensorModel):
    pm10_min = models.FloatField(_("PM10_min"))
    pm10_max = models.FloatField(_("PM10_max"))
    pm25_min = models.FloatField(_("PM2.5_min"))
    pm25_max = models.FloatField(_("PM2.5_max"))

    class Meta:
        abstract = True


class OSPM(ParticleSensorModel, TemperatureSensor):
    pk = models.CompositePrimaryKey(
        "created_datetime", "device_id", verbose_name=_("PK")
    )
    flow = models.FloatField(_("Flow"), null=True, blank=True)
    error_code = models.SmallIntegerField(
        _("Sensor error code"), null=True, blank=True, db_column="error_code"
    )
    status = models.PositiveSmallIntegerField(
        _("Status Flag"), choices=DataStatus.choices
    )

    class Meta:
        managed = False
        db_table = "device_ospm"


class OSPMHourly(ParticleSensorHourlyModel, TemperatureSensorHourly):
    pk = models.CompositePrimaryKey(
        "created_datetime", "device_id", verbose_name=_("PK")
    )
    created_datetime = models.DateTimeField(_("Created Datetime"), db_column="hour")

    class Meta:
        managed = False
        db_table = "hourly_ospm"


class OSPMDaily(ParticleSensorHourlyModel):
    pk = models.CompositePrimaryKey(
        "created_datetime", "device_id", verbose_name=_("PK")
    )
    created_datetime = models.DateTimeField(_("Created Datetime"), db_column="day")

    class Meta:
        managed = False
        db_table = "daily_ospm"


class OSPMDailyTemperature(TemperatureSensorHourly):
    pk = models.CompositePrimaryKey(
        "created_datetime", "device_id", verbose_name=_("PK")
    )
    created_datetime = models.DateTimeField(_("Created Datetime"), db_column="day")
    device_id = models.PositiveIntegerField(_("Device ID"))
    objects = models.Manager()
    timescale = MyTimescaleManager()

    class Meta:
        managed = False
        db_table = "daily_ospm_temp"
