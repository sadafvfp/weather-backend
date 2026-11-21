from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import NotFound
from datetime import datetime, timedelta
from django.conf import settings
from ..device.models import DeviceStatus, DeviceInfo
from ..device.services import InfoService, LatestDataService


class HasDeviceAccess(BasePermission):
    def has_permission(self, request, view):
        device_id = view.device_info.id
        return DeviceInfo.user.through.objects.filter(
            deviceinfo_id=device_id, user_id=request.user.id
        ).exists()


class DeviceIsActive(BasePermission):
    def has_permission(self, request, view):
        device_info = view.device_info
        return (
            device_info is not None and device_info.status != DeviceStatus.DEACTIVATED
        )


class DeviceExists(BasePermission):
    def has_permission(self, request, view):
        if view.device_info is None:
            raise NotFound("Device does not exist.")
        return True


class IsSuperuserOrAuthenticatedReadOnly(BasePermission):
    """
    - Superusers: full access
    - Other authenticated users: read-only (GET, HEAD, OPTIONS)
    - Anonymous users: no access
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return request.method in SAFE_METHODS
