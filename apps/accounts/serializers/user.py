from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from datetime import timedelta

from backend.apps.custom.serializers.fields import UsernameField, PersianDateTimeField
from backend.apps.device.models import DeviceInfo

from .fields import UserUniqueUsernameField
from ..services import UserService

User = get_user_model()


class CustomResponseSerializer(serializers.Serializer):
    is_superuser = serializers.BooleanField(
        source="user.is_superuser",
        read_only=True,
    )
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )


class ProfileSerializer(serializers.ModelSerializer):
    """A user can read their profile and change only their username."""

    username = UserUniqueUsernameField()

    class Meta:
        model = User
        fields = ("uuid", "username", "is_superuser")
        read_only_fields = ("uuid", "is_superuser")


class UserListSerializer(serializers.ModelSerializer):
    """Superuser user list: uuid, username, superuser flag, and device slugs."""

    username = UsernameField(read_only=True)
    # devices = serializers.SerializerMethodField()
    date_joined = PersianDateTimeField(interval=timedelta(minutes=1), read_only=True)
    last_login = PersianDateTimeField(interval=timedelta(minutes=1), read_only=True)

    class Meta:
        model = User
        fields = (
            "uuid",
            "username",
            "is_superuser",
            "is_active",
            "date_joined",
            "last_login",
        )
        read_only_fields = (
            "uuid",
            "username",
            "is_superuser",
            "is_active",
            "date_joined",
            "last_login",
        )

    # def get_devices(self, user):
    #     return sorted(
    #         device.slug for device in user.deviceinfo_set.all() if device.slug
    #     )


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """A superuser edits another user's username, superuser flag, and devices."""

    username = UserUniqueUsernameField()
    is_superuser = serializers.BooleanField()
    # devices = serializers.ListField(child=serializers.CharField(), allow_empty=True)

    class Meta:
        model = User
        fields = ("uuid", "username", "is_superuser", "is_active")
        read_only_fields = ("uuid",)

    # def validate_devices(self, slugs):
    #     if len(slugs) != len(set(slugs)):
    #         raise serializers.ValidationError(_("Duplicate device slug."))
    #     found = list(DeviceInfo.objects.filter(slug__in=slugs))
    #     by_slug = {}
    #     for device in found:
    #         if device.slug in by_slug:
    #             raise serializers.ValidationError(
    #                 _("More than one device uses this slug.")
    #             )
    #         by_slug[device.slug] = device
    #     missing = [slug for slug in slugs if slug not in by_slug]
    #     if missing:
    #         raise serializers.ValidationError(_("No device with this slug."))
    #     self.device_objects = [by_slug[slug] for slug in slugs]
    #     return slugs

    def update(self, instance, validated_data):
        # validated_data.pop("devices")
        is_superuser = validated_data["is_superuser"]
        instance.username = validated_data["username"]
        instance.is_active = validated_data["is_active"]
        instance.is_superuser = is_superuser
        instance.is_staff = is_superuser
        instance.save(
            update_fields=["username", "is_superuser", "is_staff", "is_active"]
        )
        # instance.deviceinfo_set.set(self.device_objects)
        return instance

    def to_representation(self, instance):
        return UserListSerializer(instance).data


# class UserDeviceSerializer(serializers.Serializer):
#     """Identify a device by the slug stored on DeviceInfo."""

#     slug = serializers.CharField()

#     def validate_slug(self, value):
#         matches = list(DeviceInfo.objects.filter(slug=value)[:2])
#         if not matches:
#             raise serializers.ValidationError(_("No device with this slug."))
#         if len(matches) > 1:
#             raise serializers.ValidationError(_("More than one device uses this slug."))
#         self.device = matches[0]
#         return value


class AdminUserSerializer(serializers.ModelSerializer):
    """Superuser creates either another superuser or a regular user."""

    username = UserUniqueUsernameField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    re_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    is_superuser = serializers.BooleanField()
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = User
        fields = (
            "uuid",
            "username",
            "password",
            "re_password",
            "is_superuser",
            "is_active",
        )
        read_only_fields = ("uuid",)

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if actor is None or not actor.is_authenticated or not actor.is_superuser:
            raise serializers.ValidationError(_("Only a superuser can create users."))
        if attrs["password"] != attrs["re_password"]:
            raise serializers.ValidationError(
                {"re_password": _("The two password fields didn’t match.")}
            )
        candidate = User(username=attrs["username"])
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("re_password")
        is_superuser = validated_data["is_superuser"]
        is_active = validated_data.get("is_active", True)
        user = User(
            username=validated_data["username"],
            is_superuser=is_superuser,
            is_staff=is_superuser,
            is_active=is_active,
        )
        user.set_password(password)
        user.save()
        return user


class SetPasswordSerializer(serializers.Serializer):
    """A superuser sets a new password for someone else."""

    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    re_new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(
                value, user=self.context.get("target_user")
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["re_new_password"]:
            raise serializers.ValidationError(
                {"re_new_password": _("The two password fields didn’t match.")}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={"blank": _("This field may not be blank.")},
    )
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={"blank": _("This field may not be blank.")},
    )
    re_new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={"blank": _("This field may not be blank.")},
    )

    def to_representation(self, instance):
        return {}

    def create(self, validated_data):
        raise NotImplementedError("`create()` must be implemented.")

    def update(self, instance, validated_data):
        return UserService.change_password(
            user=instance, new_password=validated_data["new_password"]
        )

    def validate_current_password(self, value):
        if self.instance and UserService.check_password(
            user=self.instance, password=value
        ):
            return value
        raise ValidationError(_("Current password has been entered wrong !"))

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value, user=self.instance)
        except DjangoValidationError as exc:
            raise ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["re_new_password"]:
            raise ValidationError(
                {"re_new_password": _("The two password fields didn’t match.")}
            )
        if attrs["current_password"] == attrs["new_password"]:
            raise ValidationError(
                _("New password and current password should not be same !")
            )
        return attrs
