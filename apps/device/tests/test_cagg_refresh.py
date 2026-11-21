from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import SimpleTestCase
from django.utils import timezone

from backend.apps.mytimescale.cagg_refresh import (
    expand_refresh_window,
    floor_time_bucket,
    HOURLY_OSPM_ORIGIN,
    refresh_window_for_ospm_deletion,
)


class CaggWindowTests(SimpleTestCase):
    def test_floor_time_bucket_respects_origin(self):
        ts = timezone.make_aware(datetime(2026, 1, 2, 10, 15, 0))
        floored = floor_time_bucket(ts, timedelta(hours=1), HOURLY_OSPM_ORIGIN)
        self.assertEqual(floored.hour, 10)
        self.assertEqual(floored.minute, 0)

    def test_refresh_windows_cover_deleted_range(self):
        start = timezone.make_aware(datetime(2026, 3, 1, 10, 3, 0))
        end = timezone.make_aware(datetime(2026, 3, 1, 10, 9, 0))
        windows = refresh_window_for_ospm_deletion(start, end)
        self.assertEqual(len(windows), 4)
        views = {name for name, _, _ in windows}
        self.assertEqual(
            views,
            {"hourly_ospm", "hourly_ospm_temp", "daily_ospm", "daily_ospm_temp"},
        )
        for _, w_start, w_end in windows:
            self.assertLessEqual(w_start, start)
            self.assertGreaterEqual(w_end, end)

    def test_expand_refresh_window_swaps_inverted_bounds(self):
        start = timezone.make_aware(datetime(2026, 3, 2, 12, 0, 0))
        end = timezone.make_aware(datetime(2026, 3, 2, 10, 0, 0))
        w_start, w_end = expand_refresh_window(
            start, end, timedelta(hours=1), HOURLY_OSPM_ORIGIN
        )
        self.assertLessEqual(w_start, w_end)
