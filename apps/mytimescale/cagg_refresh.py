import logging
import math
from datetime import datetime, timedelta, timezone as dt_timezone

from django.core.cache import cache
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

REFRESH_LOCK_TTL_SECONDS = 30 * 60

HOURLY_OSPM_ORIGIN = timezone.make_aware(
    datetime(2000, 1, 1, 10, 0, 0), dt_timezone(timedelta(hours=3, minutes=30))
)
HOURLY_OSPM_TEMP_ORIGIN = timezone.make_aware(
    datetime(2000, 1, 1, 0, 0, 0), dt_timezone(timedelta(hours=3, minutes=30))
)

OSPM_CONTINUOUS_AGGREGATES = (
    {
        "view": "hourly_ospm",
        "bucket": timedelta(hours=1),
        "origin": HOURLY_OSPM_ORIGIN,
        "depends_on": "device_ospm",
    },
    {
        "view": "hourly_ospm_temp",
        "bucket": timedelta(hours=1),
        "origin": HOURLY_OSPM_TEMP_ORIGIN,
        "depends_on": "device_ospm",
    },
    {
        "view": "daily_ospm",
        "bucket": timedelta(days=1),
        "origin": HOURLY_OSPM_ORIGIN,
        "depends_on": "hourly_ospm",
    },
    {
        "view": "daily_ospm_temp",
        "bucket": timedelta(days=1),
        "origin": HOURLY_OSPM_TEMP_ORIGIN,
        "depends_on": "hourly_ospm_temp",
    },
)


class ContinuousAggregateRefreshBusy(Exception):
    pass


def _ensure_aware(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(timezone.get_current_timezone())


def floor_time_bucket(ts, interval, origin):
    ts = _ensure_aware(ts)
    origin = _ensure_aware(origin)
    interval_seconds = interval.total_seconds()
    delta = (ts - origin).total_seconds()
    index = math.floor(delta / interval_seconds)
    return origin + timedelta(seconds=index * interval_seconds)


def ceil_time_bucket(ts, interval, origin):
    ts = _ensure_aware(ts)
    floored = floor_time_bucket(ts, interval, origin)
    if floored == ts:
        return floored
    return floored + interval


def expand_refresh_window(start, end, bucket, origin):
    start = _ensure_aware(start)
    end = _ensure_aware(end)
    if end < start:
        start, end = end, start
    return floor_time_bucket(start, bucket, origin), ceil_time_bucket(
        end, bucket, origin
    )


def refresh_window_for_ospm_deletion(deleted_start, deleted_end):
    """
    Compute per-view refresh windows after deleting raw three-minute rows.
    Returns list of (view_name, window_start, window_end).
    """
    deleted_start = _ensure_aware(deleted_start)
    deleted_end = _ensure_aware(deleted_end)

    hourly_ospm_start, hourly_ospm_end = expand_refresh_window(
        deleted_start, deleted_end, timedelta(hours=1), HOURLY_OSPM_ORIGIN
    )
    hourly_temp_start, hourly_temp_end = expand_refresh_window(
        deleted_start, deleted_end, timedelta(hours=1), HOURLY_OSPM_TEMP_ORIGIN
    )

    daily_ospm_start, daily_ospm_end = expand_refresh_window(
        hourly_ospm_start, hourly_ospm_end, timedelta(days=1), HOURLY_OSPM_ORIGIN
    )
    daily_temp_start, daily_temp_end = expand_refresh_window(
        hourly_temp_start,
        hourly_temp_end,
        timedelta(days=1),
        HOURLY_OSPM_TEMP_ORIGIN,
    )

    return [
        ("hourly_ospm", hourly_ospm_start, hourly_ospm_end),
        ("hourly_ospm_temp", hourly_temp_start, hourly_temp_end),
        ("daily_ospm", daily_ospm_start, daily_ospm_end),
        ("daily_ospm_temp", daily_temp_start, daily_temp_end),
    ]


def _refresh_lock_key(view_name):
    return f"ospm_cagg_refresh:{view_name}"


def refresh_continuous_aggregate(view_name, start, end):
    lock_key = _refresh_lock_key(view_name)
    if not cache.add(lock_key, "1", REFRESH_LOCK_TTL_SECONDS):
        raise ContinuousAggregateRefreshBusy(
            f"Refresh already in progress for {view_name}"
        )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL refresh_continuous_aggregate(%s, %s, %s);",
                [view_name, start, end],
            )
    finally:
        cache.delete(lock_key)


def refresh_ospm_aggregates_for_deletion(deleted_start, deleted_end):
    windows = refresh_window_for_ospm_deletion(deleted_start, deleted_end)
    refreshed = []
    for view_name, start, end in windows:
        refresh_continuous_aggregate(view_name, start, end)
        refreshed.append(
            {
                "view": view_name,
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        )
        logger.info(
            "Refreshed continuous aggregate %s from %s to %s",
            view_name,
            start,
            end,
        )
    return refreshed
