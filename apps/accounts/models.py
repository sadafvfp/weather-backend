from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from uuid import uuid4
from ..custom.models.fields import MobileNumberField


# Create your models here.
class User(AbstractUser):
    """
    A class implementing a fully featured User model with admin-compliant
    permissions.

    Email and password are required. Other fields are optional.
    """

    uuid = models.UUIDField(_("UUID"), unique=True, default=uuid4, editable=False)
    mobile_number = MobileNumberField(
        _("Mobile Number"),
        unique=True,
        blank=True,
        null=True,
        error_messages={"unique": _("The mobile number is already taken.")},
    )
    is_mobile_verified = models.BooleanField(
        _("Mobile Verified"),
        default=False,
        help_text=_("Whether this user has verified his mobile number or not"),
    )

    def sms_user(self):
        pass


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
