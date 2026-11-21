from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.cache import cache
from django.db import OperationalError
from datetime import timedelta, datetime
from celery import shared_task
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
import json
import logging


from .services import HistoryDataService, CAGG_MIN_AGE
from backend.apps.mytimescale.cagg_refresh import (
    ContinuousAggregateRefreshBusy,
    refresh_ospm_aggregates_for_deletion,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
HOURLY_RETRY_DELAY = 30 * 60  # 5 minutes (adjust to your CAGG refresh policy)
DAILY_RETRY_DELAY = 60 * 60  # 1 hour: daily CAGGs are built on the hourly CAGG


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
    reject_on_worker_lost=True,
)
def history_data_store(self, payload):
    payload = {
        **payload,
        "created_datetime": parse_datetime(payload["created_datetime"]),
    }
    try:
        HistoryDataService.store_reading(payload)
    except OperationalError as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def refresh_ospm_continuous_aggregates(self, start_iso, end_iso):
    start = parse_datetime(start_iso)
    end = parse_datetime(end_iso)
    try:
        refresh_ospm_aggregates_for_deletion(start, end)
    except ContinuousAggregateRefreshBusy as exc:
        logger.warning("OSPM aggregate refresh busy, retrying: %s", exc)
        raise self.retry(exc=exc)
    except OperationalError as exc:
        logger.exception("OSPM aggregate refresh failed")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
)
def flush_pending_ospm_cagg_refresh(self, device_id, expected_version):
    """
    Fallback task: If a multi-batch upload is interrupted before batch_id == total_batch
    arrives, this runs after 5 minutes of inactivity for `device_id`.
    If `version` matches `expected_version` (meaning no newer batch arrived in the meantime),
    it flushes the accumulated [min_ts, max_ts] window and triggers CAGG refresh.
    """
    win_key = HistoryDataService._cagg_window_key(device_id)
    state = cache.get(win_key)
    if not state:
        return

    if state.get("version") != expected_version:
        # A newer batch arrived after this timer was scheduled; the newer timer or final batch will handle it.
        return

    cache.delete(win_key)
    min_ts = state.get("min_ts")
    max_ts = state.get("max_ts")
    if not min_ts or not max_ts:
        return

    min_dt = parse_datetime(min_ts)
    now = timezone.localtime(timezone.now())
    if min_dt is not None and (now - min_dt) >= CAGG_MIN_AGE:
        logger.info(
            "Fallback CAGG refresh triggered for interrupted backfill on device %s (%s -> %s)",
            device_id,
            min_ts,
            max_ts,
        )
        refresh_ospm_continuous_aggregates.delay(min_ts, max_ts)


# def _sync_latest(source_model, granularity, time_add=0) -> int:
#     """
#     Copy the newest row per device from `source_model` into LatestData.
#     Returns the number of LatestData rows created or updated.
#     """
#     now = datetime.now()
#     latest_rows = (
#         source_model.objects.filter(created_datetime__gte=now - timedelta(days=2))
#         .order_by("device_id", "-created_datetime")
#         .distinct("device_id")  # PostgreSQL DISTINCT ON
#         .values()
#     )

#     existing = {
#         ld.deviceinfo_id: ld
#         for ld in LatestData.objects.filter(
#             granularity=granularity, status=DataStatus.PRODUCTION
#         )
#     }

#     to_create, to_update = [], []
#     for row in latest_rows:
#         device_id = row["device_id"]
#         created_dt = row["created_datetime"] + timedelta(hours=time_add)
#         # make the row JSON-safe (datetimes, Decimals, ...)
#         data = json.loads(json.dumps(row, cls=DjangoJSONEncoder))
#         data.pop("created_datetime")
#         current = existing.get(device_id)
#         if current is None:
#             to_create.append(
#                 LatestData(
#                     deviceinfo_id=device_id,
#                     status=DataStatus.PRODUCTION,
#                     granularity=granularity,
#                     created_datetime=created_dt,
#                     data=data,
#                 )
#             )
#         elif current.created_datetime != created_dt or current.data != data:
#             current.created_datetime = created_dt
#             current.data = data
#             to_update.append(current)

#     with transaction.atomic():
#         if to_create:
#             LatestData.objects.bulk_create(to_create)
#         if to_update:
#             LatestData.objects.bulk_update(to_update, ["created_datetime", "data"])

#     return len(to_create) + len(to_update)


# def _run(task, source_model, granularity, retry_delay, time_add):
#     changed = _sync_latest(source_model, granularity, time_add)
#     if changed:
#         logger.info("LatestData[%s]: %s rows created/updated", granularity, changed)
#         return changed

#     if task.request.retries >= MAX_RETRIES:
#         logger.error(
#             "LatestData[%s]: nothing new after %s retries, giving up",
#             granularity,
#             MAX_RETRIES,
#         )
#         return 0

#     logger.warning(
#         "LatestData[%s]: nothing new, retry %s/%s in %ss",
#         granularity,
#         task.request.retries + 1,
#         MAX_RETRIES,
#         retry_delay,
#     )
#     raise task.retry(countdown=retry_delay, max_retries=MAX_RETRIES)


# @shared_task(bind=True)
# def sync_latest_hourly(self):
#     return _run(self, OSPMHourly, Granularity.HOURLY, HOURLY_RETRY_DELAY, time_add=1)


# @shared_task(bind=True)
# def sync_latest_daily(self):
#     return _run(self, OSPMDaily, Granularity.DAILY, DAILY_RETRY_DELAY, time_add=25)


# @shared_task(bind=True)
# def sync_latest_daily_temperature(self):
#     return _run(
#         self,
#         OSPMDailyTemperature,
#         Granularity.DAILY_TEMPERATURE,
#         DAILY_RETRY_DELAY,
#         time_add=25,
#     )
