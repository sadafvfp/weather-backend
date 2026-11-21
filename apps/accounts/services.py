#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAlreadyVerified(Exception):
    def __init__(self, msg="This user is already verified!"):
        super(UserAlreadyVerified, self).__init__(self, msg)


class UserService(object):
    """
    UserService class provide interface for managing users
    """

    @staticmethod
    def save(user):
        try:
            user.save()
        except IntegrityError as error:
            message = str(error)
            if "django_auth_user.email" in message:
                raise ValidationError(_("The email is already taken."))
            elif "django_auth_user.username" in message:
                raise ValidationError(_("The username is already taken."))
            elif "django_auth_user.mobile_number" in message:
                raise ValidationError(_("The mobile number is already taken."))
            raise error

    @staticmethod
    def register(
        email,
        password,
        first_name="",
        last_name="",
        mobile_number=None,
        username=None,
        groups=None,
    ):
        User = get_user_model()
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            username=username,
            is_active=True,
        )
        user.set_password(password)
        UserService.save(user)

        if groups is not None:
            for group_name in groups:
                UserService.add_user_to_group(user, group_name)

        return user

    @staticmethod
    def update_profile(
        user, username, mobile_number, is_mobile_verified, first_name, last_name
    ):
        user.username = username
        user.mobile_number = mobile_number
        user.is_mobile_verified = is_mobile_verified
        user.first_name = first_name
        user.last_name = last_name
        UserService.save(user)
        return user

    @staticmethod
    def add_user_to_group(user, group_name):
        """
        Adds user to given group name
        :param user: user instance
        :type user: :py:class:`~django_contrib.auth.models.User`
        :param group_name: name of the group which user should be added to
        :type group_name: str
        """
        group = Group.objects.get_or_create(name=group_name)[0]
        user.groups.add(group)

    @staticmethod
    def user_has_group(user, group_name):
        return user.groups.filter(name=group_name).exists()

    @staticmethod
    def get_user(*args, **kwargs):
        try:
            return User.objects.get(*args, **kwargs)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_id(id_):
        return UserService.get_user(id=id_)

    @staticmethod
    def get_user_by_uuid(uuid_):
        return UserService.get_user(uuid=uuid_)

    @staticmethod
    def verify_user(user_uuid):
        user = UserService.get_user_by_uuid(user_uuid)

        if user and user.is_active:
            if user.is_verified:
                raise UserAlreadyVerified
            user.is_verified = True
            user.save()
            return user
        return None

    @staticmethod
    def update_user_last_login(user):
        user.last_login = timezone.now()
        user.save()

    @staticmethod
    def change_password(user, new_password):
        if user is not None:
            if new_password is not None:
                user.set_password(new_password)
                user.save()
                return user
            raise AssertionError("New password should not be null !")
        return None

    @staticmethod
    def check_password(user, password):
        if user is not None:
            return user.check_password(password)
        return None
