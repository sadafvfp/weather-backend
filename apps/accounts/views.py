from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dj_rest_auth.views import LoginView

from .models import User
from .permissions import IsSuperUser
from .serializers.user import ChangePasswordSerializer
from .serializers.user import (
    AdminUserSerializer,
    ProfileSerializer,
    SetPasswordSerializer,
    # UserDeviceSerializer,
    UserListSerializer,
    UserProfileUpdateSerializer,
)
from .services import UserService
from .filters import UserFilter
from . import login_rate_limit


@method_decorator(csrf_protect, name="dispatch")
class CustomLoginView(LoginView):

    def post(self, request, *args, **kwargs):
        self.request = request
        ip = login_rate_limit.get_client_ip(request)
        username_key = login_rate_limit.normalize_username(
            request.data.get("username")
        )

        blocked = login_rate_limit.check_blocked(ip, username_key)
        if blocked is not None:
            return login_rate_limit.lockout_response(
                blocked.retry_after_seconds, blocked.scope
            )

        self.serializer = self.get_serializer(data=self.request.data)
        if not self.serializer.is_valid():
            if login_rate_limit.is_auth_failure(self.serializer.errors):
                limit_status = login_rate_limit.record_failures(ip, username_key)
                if limit_status.locked:
                    return login_rate_limit.lockout_response(
                        limit_status.retry_after_seconds or 1,
                        limit_status.scope or "ip",
                    )
                return Response(
                    {
                        **self.serializer.errors,
                        "login_rate_limit": limit_status.as_dict(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                self.serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        self.login()
        login_rate_limit.clear(ip, username_key)
        data = {
            "username": self.user.username,
            "is_superuser": self.user.is_superuser,
        }
        return Response(data, status=status.HTTP_200_OK)
        # return self.get_response()

    # def get_response(self):
    #     data = {
    #         "username": self.user.username,
    #         "is_superuser": self.user.is_superuser,
    #     }
    #     return Response(data, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    """Only a superuser can create a superuser or a regular user."""

    permission_classes = [IsSuperUser]
    serializer_class = AdminUserSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """The signed-in user can read their profile and change only their username."""

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    http_method_names = ["get", "put", "head", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Any user can change their own password after confirming the current one."""

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListView(generics.ListAPIView):
    """Only a superuser can list users, with uuid, username, and device slugs."""

    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsSuperUser]
    serializer_class = UserListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["username", "email", "first_name", "last_name"]

    # ?ordering=-date_joined,email
    ordering_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "date_joined",
        "last_login",
        "is_active",
    ]
    ordering = ["-date_joined"]


# class UserDeviceView(generics.GenericAPIView):
#     """A superuser adds or removes one device on a user, identified by slug."""

#     permission_classes = [IsSuperUser]
#     serializer_class = UserDeviceSerializer
#     queryset = User.objects.all()
#     lookup_field = "uuid"

#     def post(self, request, *args, **kwargs):
#         return self._set_device(add=True)

#     def delete(self, request, *args, **kwargs):
#         return self._set_device(add=False)

#     def _set_device(self, add):
#         target = self.get_object()
#         serializer = self.get_serializer(data=self.request.data)
#         serializer.is_valid(raise_exception=True)
#         if add:
#             serializer.device.user.add(target)
#         else:
#             serializer.device.user.remove(target)
#         return Response(UserListSerializer(target).data)


class ResetPasswordView(generics.GenericAPIView):
    """A superuser resets another user's password. They cannot reset their own."""

    permission_classes = [IsSuperUser]
    serializer_class = SetPasswordSerializer
    queryset = User.objects.all()
    lookup_field = "uuid"

    def post(self, request, *args, **kwargs):
        target = self.get_object()
        if target.pk == request.user.pk:
            raise PermissionDenied(_("You cannot reset your own password."))
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "target_user": target},
        )
        serializer.is_valid(raise_exception=True)
        UserService.change_password(
            user=target, new_password=serializer.validated_data["new_password"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """A superuser reads, edits, or deletes another user. They cannot edit or delete themselves."""

    permission_classes = [IsSuperUser]
    queryset = User.objects.all()
    lookup_field = "uuid"
    http_method_names = ["get", "put", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return UserProfileUpdateSerializer
        return UserListSerializer

    def update(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            raise PermissionDenied(_("You cannot change your own profile."))
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied(_("You cannot delete your own account."))
        instance.delete()
