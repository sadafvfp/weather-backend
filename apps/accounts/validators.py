from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.validators import UniqueValidator
from .models import User


class UserUniqueFieldValidator(object):
    """
    Validator that corresponds to `unique=True` on a user field.
    """

    message = _("This field must be unique.")
    code = "unique"

    def __init__(self, field_name, message=None, code=None):
        self.field_name = field_name
        self.message = message or self.message
        self.code = code or self.code
        self._user = None

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    def __call__(self, value):
        qs = User.objects.filter(**{self.field_name: value})
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)

        if qs.exists():
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        result = (
            isinstance(other, UserUniqueFieldValidator)
            and self.field_name == other.field_name
        )
        result = result and self.message == other.message and self.code == other.code
        return result


class UniqueUserEmailValidator(UserUniqueFieldValidator):
    """
    Validator that corresponds to `unique=True` on a user email field.
    """

    message = _("The email is already taken.")
    code = "email"

    def __init__(self, message=None, code=None):
        message = message or self.message
        code = code or self.code
        super(UniqueUserEmailValidator, self).__init__("email", message, code)


class UniqueUsernameValidator(UserUniqueFieldValidator):
    """
    Validator that corresponds to `unique=True` on a username field.
    """

    message = _("The username is already taken.")
    code = "username"

    def __init__(self, message=None, code=None):
        message = message or self.message
        code = code or self.code
        super(UniqueUsernameValidator, self).__init__("username", message, code)


class UniqueUserMobileNumberValidator(UserUniqueFieldValidator):
    """
    Validator that corresponds to `unique=True` on a mobile_number field.
    """

    message = _("The mobile number is already taken.")
    code = "mobile_number"

    def __init__(self, message=None, code=None):
        message = message or self.message
        code = code or self.code
        super(UniqueUserMobileNumberValidator, self).__init__(
            "mobile_number", message, code
        )


class UserUniqueSerializerFieldValidator(UniqueValidator):
    """
    Validator that corresponds to `unique=True` on a user field.

    Should be applied to an individual field on the serializer.
    """

    message = _("User already exists.")

    def __init__(self, message=None):
        self.message = message or self.message
        super(UserUniqueSerializerFieldValidator, self).__init__(
            User.objects.all(), self.message
        )
