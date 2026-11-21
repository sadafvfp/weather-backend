from unittest.mock import patch

from django.test import SimpleTestCase

from backend.apps.device.tasks import refresh_ospm_continuous_aggregates
from backend.apps.mytimescale.cagg_refresh import ContinuousAggregateRefreshBusy


class RefreshTaskTests(SimpleTestCase):
    @patch("backend.apps.device.tasks.refresh_ospm_aggregates_for_deletion")
    def test_refresh_task_calls_service(self, refresh):
        refresh_ospm_continuous_aggregates.run(
            "2026-01-01T00:00:00+03:30", "2026-01-02T00:00:00+03:30"
        )
        refresh.assert_called_once()

    @patch("backend.apps.device.tasks.refresh_ospm_aggregates_for_deletion")
    def test_refresh_task_retries_when_busy(self, refresh):
        refresh.side_effect = ContinuousAggregateRefreshBusy("busy")
        with patch.object(
            refresh_ospm_continuous_aggregates,
            "retry",
            side_effect=RuntimeError("retry"),
        ) as retry:
            with self.assertRaises(RuntimeError):
                refresh_ospm_continuous_aggregates.run(
                    "2026-01-01T00:00:00+03:30", "2026-01-02T00:00:00+03:30"
                )
            retry.assert_called_once()
