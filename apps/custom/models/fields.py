from django.core.validators import MinLengthValidator, RegexValidator
from django.core.validators import validate_email
from django.db import models
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


class UsernameField(models.CharField):
    default_validators = [
        RegexValidator(
            regex=r"^[A-Za-z0-9.-]+$",
            message=_(
                "Enter a valid username. This value may contain only Letters, digits and ./- ."
            ),
        )
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 30)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return value and value.lower()


class EmailField(models.EmailField):
    default_validators = [validate_email]

    def to_python(self, value):
        value = super().to_python(value)
        return value and value.lower()


class MobileNumberField(models.CharField):
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


class RoundedFloatField(models.FloatField):
    def __init__(self, *args, decimals=2, **kwargs):
        self.decimals = decimals
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)

        if value is not None:
            return round(float(value), self.decimals)

        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)

        if value is not None:
            return round(float(value), self.decimals)

        return value


class TruncatedDatetime(models.DateTimeField):

    def _round_datetime(self, value):
        if value is None:
            return value

        return value.replace(microsecond=0)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self._round_datetime(value)

    def to_python(self, value):
        value = super().to_python(value)
        return self._round_datetime(value)

    def from_db_value(self, value, expression, connection):
        return self._round_datetime(value)
