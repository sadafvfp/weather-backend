from django.db.models import Func, FloatField

from django.db import models
from timescale.db.models.expressions import Interval, TimescaleDateTimeField


class Interpolate(Func):
    function = "interpolate"
    output_field = FloatField()


class TimeBucketGapFill(models.Func):
    """
    IMplementation of the time_bucket_gapfill function from Timescale

    Read more about it here - https://docs.timescale.com/latest/using-timescaledb/reading-data#gap-filling

    Response:

    [
        ...
        {'bucket': '2020-12-22T11:36:00+00:00', 'temperature__avg': 52.7127405105567},
        {'bucket': '2020-12-22T11:42:00+00:00', 'temperature__avg': None},
        ...
    ]
    """

    function = "time_bucket_gapfill"
    name = "time_bucket_gapfill"

    def __init__(
        self,
        expression,
        interval,
        start,
        end,
        timezone,
        datapoints=None,
        *args,
        **kwargs
    ):
        if not isinstance(interval, models.Value):
            interval = Interval(interval)
            if datapoints:
                interval = interval / datapoints
        output_field = TimescaleDateTimeField(interval=interval)
        super().__init__(
            interval, expression, start, end, timezone, output_field=output_field
        )
