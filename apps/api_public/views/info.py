from django.db import transaction
from rest_framework.viewsets import ModelViewSet
from backend.apps.device.models import DeviceInfo
from backend.apps.device.permissions import IsSuperuserOrAuthenticatedReadOnly
from ..serializers.info import DeviceInfoSerializer


class DeviceInfoModelViewSet(ModelViewSet):
    queryset = DeviceInfo.objects.all()
    serializer_class = DeviceInfoSerializer
    permission_classes = [IsSuperuserOrAuthenticatedReadOnly]
    lookup_field = "slug"

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.delete()
