import os
from datetime import timedelta, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from backend.apps.api_ingestion.views import ESPSAPIView, OSPMAPIView, SAPAAPIView
from backend.apps.api_ingestion.views.base import BaseInsertDataAPIView
from backend.apps.device.exceptions import DataDropped, MunicipalityAPIError
from backend.apps.device.models import DataStatusFlag, DeviceStatusFlag
from backend.apps.device.services import IngestionService, LatestDataService
from backend.apps.device.tasks import (
    forward_reading_to_municipality,
    history_data_store,
)


@override_settings(ROOT_URLCONF="backend.urls.ingestion")
class IngestionEntrypointTests(SimpleTestCase):
    def test_ingestion_settings_module_is_loaded(self):
        self.assertEqual(
            os.environ["DJANGO_SETTINGS_MODULE"],
            "backend.settings.ingestion",
        )
        self.assertEqual(settings.ROOT_URLCONF, "backend.urls.ingestion")
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"],
            [
                "rest_framework.renderers.JSONRenderer",
            ],
        )

    def test_ingestion_urlconf_exposes_only_ingestion_device_endpoints(self):
        self.assertIs(resolve("/aqs/SAPA/").func.view_class, SAPAAPIView)
        self.assertIs(resolve("/aqs/OSPM/").func.view_class, OSPMAPIView)
        self.assertIs(resolve("/aqs/ESPS/").func.view_class, ESPSAPIView)

    def test_panel_urls_are_not_available_from_ingestion_urlconf(self):
        with self.assertRaises(Exception):
            resolve("/admin/")

    def test_manage_wsgi_and_asgi_default_to_ingestion_settings(self):
        import manage
        import backend.asgi
        import backend.wsgi

        self.assertEqual(manage.DEFAULT_SETTINGS_MODULE, "backend.settings.ingestion")
        self.assertEqual(
            backend.asgi.DEFAULT_SETTINGS_MODULE,
            "backend.settings.ingestion",
        )
        self.assertEqual(
            backend.wsgi.DEFAULT_SETTINGS_MODULE,
            "backend.settings.ingestion",
        )


class DeviceIdParsingTests(SimpleTestCase):
    factory = APIRequestFactory()

    def _view_for_request(self, request):
        view = BaseInsertDataAPIView()
        view.request = request
        view.map_dict = {"name": "device_id"}
        return view

    def test_get_device_id_accepts_querydict_name_alias(self):
        request = self.factory.get("/aqs/SAPA/", {"name": "42"})

        device_id = self._view_for_request(request).get_device_id()

        self.assertEqual(device_id, 42)

    def test_get_device_id_accepts_json_integer_device_id(self):
        request = SimpleNamespace(query_params={}, data={"device_id": 42})

        device_id = self._view_for_request(request).get_device_id()

        self.assertEqual(device_id, 42)

    def test_get_device_id_rejects_missing_device_id_cleanly(self):
        request = self.factory.get("/aqs/SAPA/", {"pm10": "12"})

        with self.assertRaises(ValidationError) as exc:
            self._view_for_request(request).get_device_id()

        self.assertEqual(
            str(exc.exception.detail["device_id"]), "This query parameter is required."
        )

    def test_get_device_id_rejects_non_integer_device_id_cleanly(self):
        request = self.factory.get("/aqs/SAPA/", {"name": "abc"})

        with self.assertRaises(ValidationError) as exc:
            self._view_for_request(request).get_device_id()

        self.assertEqual(
            str(exc.exception.detail["device_id"]), "Must be a valid integer."
        )

    def test_normalize_payload_does_not_mutate_original_payload(self):
        view = BaseInsertDataAPIView()
        view.map_dict = {"name": "device_id"}
        payload = {"name": "9", "pm10": "11"}

        normalized = view.normalize_payload(payload)

        self.assertEqual(payload, {"name": "9", "pm10": "11"})
        self.assertEqual(normalized["device_id"], "9")
        self.assertNotIn("name", normalized)

    def test_normalize_payload_flattens_single_query_values(self):
        view = BaseInsertDataAPIView()
        view.map_dict = {"name": "device_id"}

        normalized = view.normalize_payload({"name": ["9"], "pm10": ["11"]})

        self.assertEqual(normalized["device_id"], "9")
        self.assertEqual(normalized["pm10"], "11")


class IngestionAPIViewTests(SimpleTestCase):
    factory = APIRequestFactory()

    def setUp(self):
        self.device_info = SimpleNamespace(
            id=77,
            device_id=42,
            status=DeviceStatusFlag.PRODUCTION,
            forwards_to_municipality=False,
            calibration_factors=None,
        )
        self.prepared_reading = {
            "device_id": 42,
            "pm10": 12.5,
            "pm25": 8.0,
            "temperature": 22.0,
            "humidity": 44.0,
            "created_datetime": timezone.datetime(
                2026,
                1,
                2,
                3,
                4,
                5,
                tzinfo=datetime_timezone.utc,
            ),
            "status": DataStatusFlag.PRODUCTION,
        }

    def _dispatch(self, view_class, request):
        return view_class.as_view()(request)

    @patch("backend.apps.api_ingestion.views.base.history_data_store.delay")
    @patch(
        "backend.apps.api_ingestion.views.base.forward_reading_to_municipality.delay"
    )
    @patch("backend.apps.api_ingestion.views.base.IngestionService.prepare_reading")
    @patch("backend.apps.api_ingestion.views.base.InfoService.get_device_info")
    def test_get_with_name_alias_updates_latest_sync_and_queues_history_task(
        self,
        get_device_info,
        prepare_reading,
        forward_delay,
        history_delay,
    ):
        get_device_info.return_value = self.device_info
        prepare_reading.return_value = self.prepared_reading.copy()
        request = self.factory.get(
            "/aqs/OSPM/",
            {
                "name": "42",
                "pm10": "12.5",
                "pm25": "8",
                "temperature": "22",
                "humidity": "44",
            },
        )

        response = self._dispatch(OSPMAPIView, request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, "Done")
        get_device_info.assert_called_once_with("OSPM", 42)
        prepare_reading.assert_called_once()
        forward_delay.assert_not_called()
        history_delay.assert_called_once()
        self.assertEqual(history_delay.call_args.args[0], "OSPM")
        self.assertEqual(history_delay.call_args.args[1], DataStatusFlag.PRODUCTION)
        self.assertEqual(
            history_delay.call_args.args[2]["created_datetime"],
            "2026-01-02T03:04:05+00:00",
        )

    @patch("backend.apps.api_ingestion.views.base.history_data_store.delay")
    @patch(
        "backend.apps.api_ingestion.views.base.forward_reading_to_municipality.delay"
    )
    @patch("backend.apps.api_ingestion.views.base.IngestionService.prepare_reading")
    @patch("backend.apps.api_ingestion.views.base.InfoService.get_device_info")
    def test_post_json_can_forward_to_municipality_before_storing(
        self,
        get_device_info,
        prepare_reading,
        forward_delay,
        history_delay,
    ):
        self.device_info.forwards_to_municipality = True
        get_device_info.return_value = self.device_info
        prepared = {
            **self.prepared_reading,
            "so2": 1.0,
            "no2": 2.0,
            "co": 3.0,
            "o3": 4.0,
        }
        prepare_reading.return_value = prepared.copy()
        request = self.factory.post(
            "/aqs/SAPA/",
            {
                "device_id": 42,
                "so2": 1,
                "no2": 2,
                "co": 3,
                "o3": 4,
                "pm10": 12.5,
                "pm25": 8,
                "temperature": 22,
                "humidity": 44,
            },
            format="json",
        )

        response = self._dispatch(SAPAAPIView, request)

        self.assertEqual(response.status_code, 200)
        forward_delay.assert_called_once()
        history_delay.assert_called_once()
        self.assertEqual(forward_delay.call_args.args[0], "SAPA")
        self.assertEqual(forward_delay.call_args.args[1]["device_id"], 42)

    @patch("backend.apps.api_ingestion.views.base.InfoService.get_device_info")
    def test_inactive_or_unknown_device_is_forbidden_before_insert(
        self, get_device_info
    ):
        get_device_info.return_value = None
        request = self.factory.get(
            "/aqs/OSPM/",
            {
                "name": "42",
                "pm10": "12.5",
                "pm25": "8",
                "temperature": "22",
                "humidity": "44",
            },
        )

        response = self._dispatch(OSPMAPIView, request)

        self.assertEqual(response.status_code, 401)

    @patch("backend.apps.api_ingestion.views.base.InfoService.get_device_info")
    def test_invalid_sensor_payload_returns_bad_request(self, get_device_info):
        get_device_info.return_value = self.device_info
        request = self.factory.get(
            "/aqs/OSPM/",
            {
                "name": "42",
                "pm10": "not-a-number",
                "pm25": "8",
                "temperature": "22",
                "humidity": "44",
            },
        )

        response = self._dispatch(OSPMAPIView, request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("pm10", response.data)


class IngestionServiceTests(SimpleTestCase):
    @override_settings(
        MIN_GAP_MAP={
            DataStatusFlag.TEST: timedelta(seconds=30),
            DataStatusFlag.PRODUCTION: timedelta(seconds=120),
            DataStatusFlag.SUSPICIOUS: timedelta(seconds=60),
        }
    )
    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_test_device_creates_test_bucket_reading(self, try_accept_and_store):
        try_accept_and_store.return_value = True
        device_info = SimpleNamespace(
            id=77,
            device_id=42,
            status=DeviceStatusFlag.TEST,
            calibration_factors=None,
        )

        result = IngestionService.prepare_reading(device_info, {"pm10": 10.0})

        self.assertEqual(result["device_id"], 42)
        self.assertEqual(result["status"], DataStatusFlag.TEST)
        self.assertIn("created_datetime", result)
        try_accept_and_store.assert_called_once()
        self.assertEqual(try_accept_and_store.call_args.args[0], 77)
        self.assertEqual(try_accept_and_store.call_args.args[1], DataStatusFlag.TEST)

    @override_settings(
        MIN_GAP_MAP={
            DataStatusFlag.TEST: timedelta(seconds=30),
            DataStatusFlag.PRODUCTION: timedelta(seconds=120),
            DataStatusFlag.SUSPICIOUS: timedelta(seconds=60),
        }
    )
    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_production_device_marks_out_of_range_sensor_as_suspicious(
        self, try_accept_and_store
    ):
        try_accept_and_store.return_value = True
        device_info = SimpleNamespace(
            id=77,
            device_id=42,
            status=DeviceStatusFlag.PRODUCTION,
            calibration_factors=None,
        )

        result = IngestionService.prepare_reading(device_info, {"pm10": 999.0})

        self.assertEqual(result["status"], DataStatusFlag.SUSPICIOUS)
        try_accept_and_store.assert_called_once()
        self.assertEqual(
            try_accept_and_store.call_args.args[1], DataStatusFlag.SUSPICIOUS
        )

    @override_settings(
        MIN_GAP_MAP={
            DataStatusFlag.TEST: timedelta(seconds=30),
            DataStatusFlag.PRODUCTION: timedelta(seconds=120),
            DataStatusFlag.SUSPICIOUS: timedelta(seconds=60),
        }
    )
    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_reading_inside_min_gap_is_dropped(self, try_accept_and_store):
        try_accept_and_store.return_value = False
        device_info = SimpleNamespace(
            id=77,
            device_id=42,
            status=DeviceStatusFlag.PRODUCTION,
            calibration_factors=None,
        )

        with self.assertRaises(DataDropped):
            IngestionService.prepare_reading(device_info, {"pm10": 10.0})

    @override_settings(
        MIN_GAP_MAP={
            DataStatusFlag.TEST: timedelta(seconds=30),
            DataStatusFlag.PRODUCTION: timedelta(seconds=120),
            DataStatusFlag.SUSPICIOUS: timedelta(seconds=60),
        }
    )
    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_calibration_is_applied_before_threshold_classification(
        self, try_accept_and_store
    ):
        try_accept_and_store.return_value = True
        device_info = SimpleNamespace(
            id=77,
            device_id=42,
            status=DeviceStatusFlag.PRODUCTION,
            calibration_factors={"pm10": 2},
        )

        result = IngestionService.prepare_reading(device_info, {"pm10": 260.0})

        self.assertEqual(result["pm10"], 520.0)
        self.assertEqual(result["status"], DataStatusFlag.SUSPICIOUS)


class LatestDataServiceTests(SimpleTestCase):
    def test_try_accept_and_store_updates_existing_old_latest_row(self):
        manager = Mock()
        queryset = Mock()
        manager.filter.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.update.return_value = 1
        new_datetime = timezone.datetime(
            2026,
            1,
            2,
            3,
            4,
            5,
            tzinfo=datetime_timezone.utc,
        )

        with patch("backend.apps.device.services.LatestData.objects", manager):
            accepted = LatestDataService.try_accept_and_store(
                77,
                DataStatusFlag.PRODUCTION,
                new_datetime,
                {"device_id": 42, "pm10": 10},
                timedelta(seconds=120),
            )

        self.assertTrue(accepted)
        queryset.update.assert_called_once_with(
            created_datetime=new_datetime,
            data={
                "device_id": 42,
                "pm10": 10,
                "created_datetime": "2026-01-02T03:04:05+00:00",
            },
        )
        manager.get_or_create.assert_not_called()

    def test_try_accept_and_store_creates_missing_latest_row(self):
        manager = Mock()
        queryset = Mock()
        manager.filter.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.update.return_value = 0
        manager.get_or_create.return_value = (Mock(), True)
        new_datetime = timezone.datetime(
            2026,
            1,
            2,
            3,
            4,
            5,
            tzinfo=datetime_timezone.utc,
        )

        with patch("backend.apps.device.services.LatestData.objects", manager):
            accepted = LatestDataService.try_accept_and_store(
                77,
                DataStatusFlag.PRODUCTION,
                new_datetime,
                {"device_id": 42, "pm10": 10},
                timedelta(seconds=120),
            )

        self.assertTrue(accepted)
        manager.get_or_create.assert_called_once_with(
            device_id=77,
            status=DataStatusFlag.PRODUCTION,
            granularity=0,
            defaults={
                "created_datetime": new_datetime,
                "data": {
                    "device_id": 42,
                    "pm10": 10,
                    "created_datetime": "2026-01-02T03:04:05+00:00",
                },
            },
        )

    def test_try_accept_and_store_drops_existing_too_recent_latest_row(self):
        manager = Mock()
        queryset = Mock()
        manager.filter.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.update.return_value = 0
        manager.get_or_create.return_value = (Mock(), False)
        new_datetime = timezone.datetime(
            2026,
            1,
            2,
            3,
            4,
            5,
            tzinfo=datetime_timezone.utc,
        )

        with patch("backend.apps.device.services.LatestData.objects", manager):
            accepted = LatestDataService.try_accept_and_store(
                77,
                DataStatusFlag.PRODUCTION,
                new_datetime,
                {"device_id": 42, "pm10": 10},
                timedelta(seconds=120),
            )

        self.assertFalse(accepted)


class IngestionCeleryTaskTests(SimpleTestCase):
    @patch("backend.apps.device.tasks.MunicipalityForwardingService.forward")
    def test_forward_task_calls_forwarding_service(self, forward):
        forward_reading_to_municipality.run("SAPA", {"device_id": 42})

        forward.assert_called_once_with("SAPA", {"device_id": 42})

    @patch("backend.apps.device.tasks.MunicipalityForwardingService.forward")
    def test_forward_task_retries_retryable_municipality_errors(self, forward):
        forward.side_effect = MunicipalityAPIError("timeout")

        with patch.object(
            forward_reading_to_municipality,
            "retry",
            side_effect=RuntimeError("retry scheduled"),
        ) as retry:
            with self.assertRaises(RuntimeError):
                forward_reading_to_municipality.run("SAPA", {"device_id": 42})

        retry.assert_called_once()

    @patch("backend.apps.device.tasks.HistoryDataService.store_reading")
    def test_history_task_parses_created_datetime_before_storing(self, store_reading):
        payload = {
            "device_id": 42,
            "pm10": 10,
            "created_datetime": "2026-01-02T03:04:05+00:00",
        }

        history_data_store.run("OSPM", DataStatusFlag.PRODUCTION, payload)

        stored_payload = store_reading.call_args.args[2]
        self.assertEqual(
            store_reading.call_args.args[:2], ("OSPM", DataStatusFlag.PRODUCTION)
        )
        self.assertEqual(stored_payload["device_id"], 42)
        self.assertEqual(
            stored_payload["created_datetime"].isoformat(), "2026-01-02T03:04:05+00:00"
        )
