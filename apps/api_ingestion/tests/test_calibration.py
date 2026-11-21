from django.test import TestCase
from types import SimpleNamespace

from ...device.calibration import (
    MULTIPLY,
    DIVIDE,
    apply_calibration_rule,
    apply_device_calibration,
)


class ApplyCalibrationRuleTests(TestCase):

    def test_none_rule_returns_original_value(self):
        value = 100

        result = apply_calibration_rule(value, None)

        self.assertEqual(result, 100)

    def test_numeric_rule_multiplies_value(self):
        result = apply_calibration_rule(100, 2)

        self.assertEqual(result, 200)

    def test_dict_multiply_rule(self):
        rule = {
            "operation": MULTIPLY,
            "value": 3,
        }

        result = apply_calibration_rule(100, rule)

        self.assertEqual(result, 300)

    def test_dict_divide_rule(self):
        rule = {
            "operation": DIVIDE,
            "value": 2,
        }

        result = apply_calibration_rule(100, rule)

        self.assertEqual(result, 50)

    def test_dict_without_operation_defaults_to_multiply(self):
        rule = {
            "value": 3,
        }

        result = apply_calibration_rule(100, rule)

        self.assertEqual(result, 300)

    def test_dict_range_applies_when_value_is_inside_range(self):
        rule = {
            "operation": MULTIPLY,
            "value": 3,
            "range": [400, 500],
        }

        result = apply_calibration_rule(450, rule)

        self.assertEqual(result, 1350)

    def test_dict_range_does_not_apply_when_value_is_outside_range(self):
        rule = {
            "operation": MULTIPLY,
            "value": 3,
            "range": [400, 500],
        }

        result = apply_calibration_rule(300, rule)

        self.assertEqual(result, 300)

    def test_dict_range_includes_minimum_boundary(self):
        rule = {
            "operation": MULTIPLY,
            "value": 2,
            "range": [400, 500],
        }

        result = apply_calibration_rule(400, rule)

        self.assertEqual(result, 800)

    def test_dict_range_includes_maximum_boundary(self):
        rule = {
            "operation": MULTIPLY,
            "value": 2,
            "range": [400, 500],
        }

        result = apply_calibration_rule(500, rule)

        self.assertEqual(result, 1000)

    def test_list_rule_applies_matching_range(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [400, 500],
            },
            {
                "operation": MULTIPLY,
                "value": 5,
                "range": [300, 399],
            },
        ]

        result = apply_calibration_rule(350, rule)

        self.assertEqual(result, 1750)

    def test_list_rule_returns_original_value_when_no_range_matches(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [400, 500],
            },
        ]

        result = apply_calibration_rule(300, rule)

        self.assertEqual(result, 300)

    def test_list_rule_uses_first_matching_rule(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [300, 500],
            },
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [400, 600],
            },
        ]

        result = apply_calibration_rule(450, rule)

        self.assertEqual(result, 900)

    def test_unsupported_operation_raises_error(self):
        rule = {
            "operation": "invalid",
            "value": 3,
        }

        with self.assertRaises(ValueError):
            apply_calibration_rule(100, rule)


class ApplyDeviceCalibrationTests(TestCase):

    def test_calibrates_multiple_fields(self):
        device_info = SimpleNamespace(
            calibration_factors={
                "pm10": {
                    "operation": MULTIPLY,
                    "value": 2,
                },
                "pm25": {
                    "operation": DIVIDE,
                    "value": 2,
                },
            }
        )

        data = {
            "pm10": 100,
            "pm25": 50,
            "temperature": 25,
        }

        result = apply_device_calibration(device_info, data)

        self.assertEqual(result["pm10"], 200)
        self.assertEqual(result["pm25"], 25)

        # Fields without calibration rules remain unchanged
        self.assertEqual(result["temperature"], 25)

    def test_skips_none_values(self):
        device_info = SimpleNamespace(
            calibration_factors={
                "pm10": {
                    "operation": MULTIPLY,
                    "value": 2,
                },
            }
        )

        data = {
            "pm10": None,
        }

        result = apply_device_calibration(device_info, data)

        self.assertIsNone(result["pm10"])

    def test_ignores_calibration_fields_missing_from_data(self):
        device_info = SimpleNamespace(
            calibration_factors={
                "pm10": {
                    "operation": MULTIPLY,
                    "value": 2,
                },
            }
        )

        data = {
            "temperature": 25,
        }

        result = apply_device_calibration(device_info, data)

        self.assertEqual(result["temperature"], 25)
        self.assertNotIn("pm10", result)

    def test_empty_calibration_factors_returns_data_unchanged(self):
        device_info = SimpleNamespace(calibration_factors={})

        data = {
            "pm10": 100,
            "temperature": 25,
        }

        result = apply_device_calibration(device_info, data)

        self.assertEqual(result["pm10"], 100)
        self.assertEqual(result["temperature"], 25)

    def test_none_calibration_factors_returns_data_unchanged(self):
        device_info = SimpleNamespace(calibration_factors=None)

        data = {
            "pm10": 100,
        }

        result = apply_device_calibration(device_info, data)

        self.assertEqual(result["pm10"], 100)

    def test_device_calibration_with_range_rule(self):
        device_info = SimpleNamespace(
            calibration_factors={
                "pm10": {
                    "operation": MULTIPLY,
                    "value": 3,
                    "range": [400, 500],
                }
            }
        )

        data = {
            "pm10": 450,
        }

        result = apply_device_calibration(device_info, data)

        self.assertEqual(result["pm10"], 1350)
