from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.accounts.permissions import IsSuperUser
from backend.apps.device.models import DeviceInfo
from backend.apps.device.ospm_deletion import parse_deletion_status_param
from backend.apps.device.services import OSPMThreeMinuteDeletionService
from backend.apps.device.tasks import refresh_ospm_continuous_aggregates

from ..serializers.ospm_admin import OSPMThreeMinuteDeleteSerializer


class OSPMThreeMinuteDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request, device_id):
        if not DeviceInfo.objects.filter(device_id=device_id).exists():
            raise NotFound("Device does not exist.")

        serializer = OSPMThreeMinuteDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        is_single_record = validated.get("created_datetime") is not None
        statuses = parse_deletion_status_param(
            request.query_params.get("status"),
            allow_both=not is_single_record,
        )

        with transaction.atomic():
            deleted_count, refresh_start, refresh_end = (
                OSPMThreeMinuteDeletionService.delete_for_device(
                    device_id, validated, statuses
                )
            )
            aggregate_refresh = "skipped"
            if deleted_count and refresh_start is not None and refresh_end is not None:
                aggregate_refresh = "pending"
                start_iso = refresh_start.isoformat()
                end_iso = refresh_end.isoformat()
                transaction.on_commit(
                    lambda: refresh_ospm_continuous_aggregates.delay(start_iso, end_iso)
                )

        return Response(
            {
                "deleted_count": deleted_count,
                "aggregate_refresh": aggregate_refresh,
            },
            status=status.HTTP_200_OK,
        )
