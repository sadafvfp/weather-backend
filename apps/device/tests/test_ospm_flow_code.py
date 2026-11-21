from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from backend.apps.api_ingestion.serializers import OSPMSerializer
from backend.apps.api_public.serializers.base import AirDataSerializer
from backend.apps.api_public.serializers.history import PublicAirSerializer1
from backend.apps.device.models import DataStatus, DeviceStatus, OSPM
from backend.apps.device.sensor_codes import (
    has_sensor_error,
    normalize_error_code,
    parse_error_code,
    sensor_error_code_label,
)
from backend.apps.device.services import IngestionService, OSPMThreeMinuteDeletionService
from backend.apps.device.utils import normalize_three_minute_datetime


class ErrorCodeParsingTests(SimpleTestCase):
    def test_code_zero_means_healthy(self):
        self.assertEqual(parse_error_code("0"), 0)
        self.assertEqual(parse_error_code(0), 0)
        self.assertFalse(has_sensor_error(0))

    def test_single_integer_code(self):
        self.assertEqual(parse_error_code("4"), 4)
        self.assertEqual(parse_error_code(12), 12)
        self.assertTrue(has_sensor_error(4))

    def test_malformed_code_rejected(self):
        with self.assertRaises(ValidationError):
            parse_error_code("1,a")
        with self.assertRaises(ValidationError):
            parse_error_code("1,2")

    @override_settings(
        OSPM_SENSOR_ERROR_CODES={1: "PM2.5", 12: "ترکیبی", 99: "سفارشی"}
    )
    def test_configurable_labels(self):
        self.assertEqual(sensor_error_code_label(1), "PM2.5")
        self.assertEqual(sensor_error_code_label(12), "ترکیبی")
        self.assertEqual(sensor_error_code_label(99), "سفارشی")

    def test_missing_code_is_optional(self):
        self.assertIsNone(parse_error_code(None))
        self.assertIsNone(normalize_error_code(None))


class IngestionSerializerTests(SimpleTestCase):
    def test_accepts_flow_and_error_code(self):
        serializer = OSPMSerializer(
            data={
                "pm10": 1.0,
                "pm25": 1.0,
                "temperature": 20.0,
                "humidity": 40.0,
                "flow": 12.5,
                "error_code": 4,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["error_code"], 4)
        self.assertEqual(serializer.validated_data["flow"], 12.5)


class IngestionSuspiciousTests(SimpleTestCase):
    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_nonzero_code_marks_suspicious_in_range(self, try_accept):
        try_accept.return_value = True
        device_info = Mock(
            device_id=42, status=DeviceStatus.PRODUCTION, spec=["device_id", "status"]
        )
        payload = {
            "pm10": 10.0,
            "pm25": 8.0,
            "temperature": 22.0,
            "humidity": 44.0,
            "error_code": 1,
        }
        result = IngestionService.prepare_reading(device_info, payload)
        self.assertEqual(result["status"], DataStatus.SUSPICIOUS)

    @patch("backend.apps.device.services.LatestDataService.try_accept_and_store")
    def test_out_of_range_still_suspicious(self, try_accept):
        try_accept.return_value = True
        device_info = Mock(
            device_id=42, status=DeviceStatus.PRODUCTION, spec=["device_id", "status"]
        )
        result = IngestionService.prepare_reading(device_info, {"pm10": 999.0})
        self.assertEqual(result["status"], DataStatus.SUSPICIOUS)


class ThreeMinuteNormalizationTests(SimpleTestCase):
    def test_normalizes_to_three_minute_bucket(self):
        tz = timezone.get_current_timezone()
        dt = timezone.make_aware(timezone.datetime(2026, 1, 2, 10, 7, 59), tz)
        normalized = normalize_three_minute_datetime(dt)
        self.assertEqual(normalized.minute, 6)
        self.assertEqual(normalized.second, 0)


@pytest.mark.django_db
def test_three_minute_fields_not_on_hourly_model_fields():
    from backend.apps.device.models import OSPMHourly

    names = {f.name for f in OSPMHourly._meta.fields}
    assert "flow" not in names
    assert "error_code" not in names


class PublicSerializerTests(SimpleTestCase):
    def test_history_includes_flow_and_error_code(self):
        row = {
            "bucket": timezone.now(),
            "pm10": 1.0,
            "pm25": 2.0,
            "temperature": 3.0,
            "humidity": 4.0,
            "flow": 5.5,
            "error_code": 4,
            "has_record": 1,
        }
        data = PublicAirSerializer1(row, context={"view": Mock(time_add=timedelta())}).data
        self.assertEqual(data["flow"], 5.5)
        self.assertEqual(data["error_code"], 4)
        self.assertEqual(data["error_code_label"], "سنسور دما")
        self.assertTrue(data["has_record"])

    @override_settings(
        OSPM_SENSOR_ERROR_CODES={4: "سنسور دما"},
    )
    def test_history_gapfill_bucket_has_no_record(self):
        row = {
            "bucket": timezone.now(),
            "pm10": None,
            "has_record": 0,
        }
        data = PublicAirSerializer1(row, context={"view": Mock(time_add=timedelta())}).data
        self.assertFalse(data["has_record"])

    @override_settings(OSPM_SENSOR_ERROR_CODES={2: "سنسور لایت اسکتر"})
    def test_latest_data_json_includes_error_code_label(self):
        payload = {
            "pm10": 1.0,
            "pm25": 2.0,
            "flow": 3.0,
            "error_code": 2,
        }
        data = AirDataSerializer(payload).data
        self.assertEqual(data["error_code"], 2)
        self.assertEqual(data["error_code_label"], "سنسور لایت اسکتر")


@pytest.mark.django_db
def test_ospm_deletion_normalizes_single_timestamp():
    device = __import__(
        "backend.apps.device.models", fromlist=["DeviceInfo"]
    ).DeviceInfo.objects.create(
        device_id=9001,
        province="تهران",
        city="تهران",
        station_name="حذف تست",
    )
    tz = timezone.get_current_timezone()
    bucket = timezone.make_aware(timezone.datetime(2026, 5, 1, 12, 7, 0), tz)
    OSPM.objects.create(
        created_datetime=bucket,
        device_id=device.device_id,
        pm10=1,
        pm25=1,
        temperature=1,
        humidity=1,
        status=DataStatus.PRODUCTION,
    )
    requested = bucket + timedelta(minutes=1, seconds=30)
    deleted, start, end = OSPMThreeMinuteDeletionService.delete_for_device(
        device.device_id,
        {"created_datetime": requested},
        [DataStatus.PRODUCTION],
    )
    assert deleted == 1
    assert start == bucket
    assert OSPM.objects.filter(device_id=device.device_id).count() == 0
