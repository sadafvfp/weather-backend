from django.core.validators import MinLengthValidator, RegexValidator
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import CharField, DateTimeField, FloatField
from rest_framework.serializers import EmailField as RestEmailField
from functools import lru_cache
from django.utils import timezone
from datetime import timedelta
import jdatetime
from backend.apps.aqi.AQICalculator import AQICalculator
from backend.apps.device.utils import match_time_format


class UsernameField(CharField):
    default_validators = [
        RegexValidator(
            regex=r"^[A-Za-z0-9.-]+$",
            message=_(
                "Enter a valid username. This value may contain only Letters, digits and ./- ."
            ),
        )
    ]

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 30)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = escape(data).lower()
        return super().to_internal_value(data)

    def to_representation(self, value):
        value = super().to_representation(value)
        if isinstance(value, str):
            return escape(value).lower()
        return value


class EmailField(RestEmailField):

    def to_internal_value(self, data):
        data = data and data.lower()
        return super().to_internal_value(data)

    def to_representation(self, value):
        value = super().to_representation(value)
        return value and value.lower()


class MobileNumberField(CharField):

    default_validators = [
        RegexValidator(
            regex=r"^09\d{9}$",
            message=_(
                "Enter a valid mobile number. This value should start with 09 and contain 11 characters ."
            ),
        )
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 11)
        super().__init__(*args, **kwargs)


class RoundedDateTimeField(DateTimeField):
    def __init__(self, *args, interval=timedelta(minutes=3), **kwargs):
        self.interval = interval
        super().__init__(*args, **kwargs)

    def to_internal_value(self, value):
        match_time_format(value, interval=self.interval)
        return super().to_internal_value(value)

    def to_representation(self, value):
        match_time_format(value, interval=self.interval)
        return super().to_representation(value)


# class QueryParamDateTimeField(DateTimeField):

#     def to_internal_value(self, value):
#         date = super().to_internal_value(value)
#         print("**************")
#         print(date)
#         print("**************")
#         return date + timedelta(hours=3, minutes=30)


@lru_cache(maxsize=4096)
def _jalali_date(d):  # d is a datetime.date
    j = jdatetime.date.fromgregorian(date=d)
    return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"


def to_persian_string(value, tz, interval=timedelta(minutes=3)):
    value = match_time_format(value, interval)
    if timezone.is_naive(value):
        value = timezone.make_aware(value, tz)
    else:
        value = value.astimezone(tz)
    return f"{_jalali_date(value.date())} {value:%H:%M:%S}"


class PersianDateTimeField(DateTimeField):
    def __init__(self, *args, interval=timedelta(minutes=3), **kwargs):
        self.interval = interval
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        return to_persian_string(value, self.default_timezone(), self.interval)


class RoundedFloatField(FloatField):
    def __init__(self, *args, places=2, **kwargs):
        self.places = places
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        return round(float(value), self.places)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return round(value, self.places)
