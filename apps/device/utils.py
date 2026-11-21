from datetime import timedelta

from django.utils import timezone

THREE_MINUTE_INTERVAL = timedelta(minutes=3)


def normalize_three_minute_datetime(dt):
    """Floor ``dt`` to the project's three-minute storage interval (Asia/Tehran)."""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    else:
        dt = dt.astimezone(timezone.get_current_timezone())
    minute = (dt.minute // 3) * 3
    return dt.replace(minute=minute, second=0, microsecond=0)


def match_time_format(dt, interval):
    if dt is None:
        return None
    interval_seconds = interval.total_seconds()
    remainder = dt.timestamp() % interval_seconds
    return dt - timedelta(seconds=remainder)


def check_threshold(value, valid_range):
    min_value, max_value = valid_range
    if min_value <= value <= max_value:
        return True
    return False
