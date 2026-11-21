from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from backend.apps.custom.serializers.fields import (
    EmailField,
    UsernameField,
    MobileNumberField,
)
from ..validators import UserUniqueSerializerFieldValidator
from ..models import User
from ..services import UserService


class UserEmailField(EmailField):

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 254)
        super(UserEmailField, self).__init__(**kwargs)
        validator = UserUniqueSerializerFieldValidator(
            message=_("The email is already taken.")
        )
        self.validators.append(validator)


class UserUniqueUsernameField(UsernameField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 30)
        super(UserUniqueUsernameField, self).__init__(**kwargs)
        validator = UserUniqueSerializerFieldValidator(
            message=_("این نام کاربری قبلا استفاده شده")
        )
        self.validators.append(validator)


class UserUniqueMobileNumberField(MobileNumberField):
    def __init__(self, **kwargs):
        super(UserUniqueMobileNumberField, self).__init__(**kwargs)
        validator = UserUniqueSerializerFieldValidator(
            message=_("The mobile number is already taken.")
        )
        self.validators.append(validator)
