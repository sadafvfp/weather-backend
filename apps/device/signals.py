from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import DeviceInfo
from .services import OSPMThreeMinuteDeletionService
from .tasks import refresh_ospm_continuous_aggregates


@receiver(pre_delete, sender=DeviceInfo)
def delete_device_history_and_refresh_cagg(sender, instance, **kwargs):
    deleted_count, refresh_start, refresh_end = (
        OSPMThreeMinuteDeletionService.delete_all_for_device(instance.device_id)
    )
    if deleted_count and refresh_start is not None and refresh_end is not None:
        start_iso = refresh_start.isoformat()
        end_iso = refresh_end.isoformat()
        transaction.on_commit(
            lambda: refresh_ospm_continuous_aggregates.delay(start_iso, end_iso)
        )
