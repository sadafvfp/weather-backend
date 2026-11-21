import pytest

from ..calibration import (
    apply_calibration_rule,
    apply_device_calibration,
    MULTIPLY,
    DIVIDE,
)

# ============================================================
# apply_calibration_rule
# ============================================================


class TestApplyCalibrationRule:
    # --------------------------------------------------------
    # No calibration
    # --------------------------------------------------------

    def test_none_rule_returns_original_value(self):
        value = 100

        result = apply_calibration_rule(value, None)

        assert result == 100

    # --------------------------------------------------------
    # Simple numeric factor
    # --------------------------------------------------------

    @pytest.mark.parametrize(
        "value, rule, expected",
        [
            (10, 2, 20),
            (10, 2.5, 25),
            (10, "2", 20),
            (10, "2.5", 25),
            (0, 5, 0),
            (-10, 2, -20),
        ],
    )
    def test_simple_numeric_factor(self, value, rule, expected):
        result = apply_calibration_rule(value, rule)

        assert result == expected

    # --------------------------------------------------------
    # Simple dictionary rule - multiplication
    # --------------------------------------------------------

    def test_dict_rule_multiply(self):
        result = apply_calibration_rule(
            10,
            {
                "operation": MULTIPLY,
                "value": 3,
            },
        )

        assert result == 30

    # --------------------------------------------------------
    # Simple dictionary rule - division
    # --------------------------------------------------------

    def test_dict_rule_divide(self):
        result = apply_calibration_rule(
            10,
            {
                "operation": DIVIDE,
                "value": 2,
            },
        )

        assert result == 5

    # --------------------------------------------------------
    # Default operation
    # --------------------------------------------------------

    def test_dict_rule_defaults_to_multiply(self):
        result = apply_calibration_rule(
            10,
            {
                "value": 3,
            },
        )

        assert result == 30

    # --------------------------------------------------------
    # Range
    # --------------------------------------------------------

    @pytest.mark.parametrize(
        "value, expected",
        [
            (300, 900),  # lower boundary included
            (350, 1050),
            (399.999, 1199.997),
        ],
    )
    def test_rule_applies_inside_range(self, value, expected):
        result = apply_calibration_rule(
            value,
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
        )

        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        "value",
        [
            299.999,
            400,  # upper boundary excluded
            500,
        ],
    )
    def test_rule_does_not_apply_outside_range(self, value):
        result = apply_calibration_rule(
            value,
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
        )

        assert result == value

    def test_range_is_min_inclusive_max_exclusive(self):
        rule = {
            "operation": MULTIPLY,
            "value": 3,
            "range": [300, 400],
        }

        assert apply_calibration_rule(300, rule) == 900
        assert apply_calibration_rule(399.999, rule) == pytest.approx(1199.997)
        assert apply_calibration_rule(400, rule) == 400

    # --------------------------------------------------------
    # Range + division
    # --------------------------------------------------------

    def test_range_rule_with_division(self):
        result = apply_calibration_rule(
            450,
            {
                "operation": DIVIDE,
                "value": 3,
                "range": [400, 500],
            },
        )

        assert result == 150

    def test_range_division_does_not_apply_outside_range(self):
        result = apply_calibration_rule(
            350,
            {
                "operation": DIVIDE,
                "value": 3,
                "range": [400, 500],
            },
        )

        assert result == 350

    # --------------------------------------------------------
    # Single rule without range
    # --------------------------------------------------------

    @pytest.mark.parametrize(
        "operation, value, factor, expected",
        [
            (MULTIPLY, 10, 3, 30),
            (DIVIDE, 10, 2, 5),
        ],
    )
    def test_single_rule_without_range(
        self,
        operation,
        value,
        factor,
        expected,
    ):
        result = apply_calibration_rule(
            value,
            {
                "operation": operation,
                "value": factor,
            },
        )

        assert result == expected

    # --------------------------------------------------------
    # Multiple conditional rules
    # --------------------------------------------------------

    def test_multiple_ranges_first_range_matches(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [400, 500],
            },
        ]

        result = apply_calibration_rule(350, rule)

        assert result == 1050

    def test_multiple_ranges_second_range_matches(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [400, 500],
            },
        ]

        result = apply_calibration_rule(450, rule)

        assert result == 900

    def test_multiple_ranges_no_range_matches(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [400, 500],
            },
        ]

        result = apply_calibration_rule(250, rule)

        assert result == 250

    def test_multiple_ranges_upper_boundary_moves_to_next_range(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [400, 500],
            },
        ]

        # 400 is excluded from [300, 400)
        # but included in [400, 500)
        result = apply_calibration_rule(400, rule)

        assert result == 800

    def test_multiple_ranges_lower_boundary(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [300, 400],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [400, 500],
            },
        ]

        result = apply_calibration_rule(300, rule)

        assert result == 900

    # --------------------------------------------------------
    # Multiple ranges with different operations
    # --------------------------------------------------------

    def test_multiple_ranges_can_use_different_operations(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
                "range": [0, 100],
            },
            {
                "operation": DIVIDE,
                "value": 2,
                "range": [100, 200],
            },
        ]

        assert apply_calibration_rule(50, rule) == 150
        assert apply_calibration_rule(100, rule) == 50
        assert apply_calibration_rule(150, rule) == 75

    # --------------------------------------------------------
    # Multiple ranges where first rule doesn't match
    # --------------------------------------------------------

    def test_skips_non_matching_rules_until_matching_rule(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 10,
                "range": [0, 100],
            },
            {
                "operation": MULTIPLY,
                "value": 2,
                "range": [200, 300],
            },
        ]

        result = apply_calibration_rule(250, rule)

        assert result == 500

    # --------------------------------------------------------
    # Multiple rules without ranges
    # --------------------------------------------------------

    def test_list_rule_without_range_uses_first_rule(self):
        rule = [
            {
                "operation": MULTIPLY,
                "value": 3,
            },
            {
                "operation": MULTIPLY,
                "value": 2,
            },
        ]

        result = apply_calibration_rule(10, rule)

        # First rule immediately matches because it has no range.
        assert result == 30

    # --------------------------------------------------------
    # Unsupported operation
    # --------------------------------------------------------

    def test_unsupported_operation_raises_value_error(self):
        rule = {
            "operation": "%",
            "value": 3,
        }

        with pytest.raises(
            ValueError,
            match=r"Unsupported calibration operation: %",
        ):
            apply_calibration_rule(10, rule)

    # --------------------------------------------------------
    # Unsupported operation in a conditional rule
    # --------------------------------------------------------

    def test_unsupported_operation_in_matching_range_raises(self):
        rule = {
            "operation": "%",
            "value": 3,
            "range": [100, 200],
        }

        with pytest.raises(
            ValueError,
            match=r"Unsupported calibration operation: %",
        ):
            apply_calibration_rule(150, rule)

    def test_unsupported_operation_outside_range_is_not_evaluated(self):
        rule = {
            "operation": "%",
            "value": 3,
            "range": [100, 200],
        }

        # Since 50 isn't in the range, the invalid operation is never reached.
        result = apply_calibration_rule(50, rule)

        assert result == 50

    # --------------------------------------------------------
    # Numeric strings as calibration values
    # --------------------------------------------------------

    @pytest.mark.parametrize(
        "rule, expected",
        [
            (
                {
                    "operation": MULTIPLY,
                    "value": "3",
                },
                30,
            ),
            (
                {
                    "operation": DIVIDE,
                    "value": "2",
                },
                5,
            ),
        ],
    )
    def test_rule_value_can_be_numeric_string(self, rule, expected):
        result = apply_calibration_rule(10, rule)

        assert result == expected

    # --------------------------------------------------------
    # Division by zero
    # --------------------------------------------------------

    def test_division_by_zero_raises_zero_division_error(self):
        with pytest.raises(ZeroDivisionError):
            apply_calibration_rule(
                10,
                {
                    "operation": DIVIDE,
                    "value": 0,
                },
            )


# ============================================================
# apply_device_calibration
# ============================================================


class TestApplyDeviceCalibration:
    # --------------------------------------------------------
    # No calibration factors
    # --------------------------------------------------------

    def test_no_calibration_factors_returns_data_unchanged(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": None,
            },
        )()

        data = {
            "pm10": 100,
            "pm25": 50,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 100,
            "pm25": 50,
        }

    def test_empty_calibration_factors_returns_data_unchanged(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {},
            },
        )()

        data = {
            "pm10": 100,
            "pm25": 50,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 100,
            "pm25": 50,
        }

    # --------------------------------------------------------
    # Single parameter
    # --------------------------------------------------------

    def test_single_parameter_multiply(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    }
                }
            },
        )()

        data = {
            "pm10": 100,
            "pm25": 50,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 300,
            "pm25": 50,
        }

    def test_single_parameter_divide(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": DIVIDE,
                        "value": 2,
                    }
                }
            },
        )()

        data = {
            "pm10": 100,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 50,
        }

    # --------------------------------------------------------
    # Multiple parameters
    # --------------------------------------------------------

    def test_multiple_parameters_are_calibrated_independently(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    },
                    "pm25": {
                        "operation": DIVIDE,
                        "value": 2,
                    },
                }
            },
        )()

        data = {
            "pm10": 100,
            "pm25": 50,
            "temperature": 25,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 300,
            "pm25": 25,
            "temperature": 25,
        }

    # --------------------------------------------------------
    # Multiple parameters with ranges
    # --------------------------------------------------------

    def test_multiple_parameters_with_ranges(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                        "range": [300, 400],
                    },
                    "pm25": {
                        "operation": DIVIDE,
                        "value": 2,
                        "range": [40, 60],
                    },
                }
            },
        )()

        data = {
            "pm10": 350,
            "pm25": 50,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 1050,
            "pm25": 25,
        }

    def test_multiple_parameters_only_matching_ranges_are_applied(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                        "range": [300, 400],
                    },
                    "pm25": {
                        "operation": MULTIPLY,
                        "value": 2,
                        "range": [40, 60],
                    },
                }
            },
        )()

        data = {
            "pm10": 500,
            "pm25": 100,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 500,
            "pm25": 100,
        }

    # --------------------------------------------------------
    # Single parameter with multiple ranges
    # --------------------------------------------------------

    def test_single_parameter_multiple_ranges(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": [
                        {
                            "operation": MULTIPLY,
                            "value": 3,
                            "range": [300, 400],
                        },
                        {
                            "operation": MULTIPLY,
                            "value": 2,
                            "range": [400, 500],
                        },
                    ]
                }
            },
        )()

        data = {
            "pm10": 350,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 1050,
        }

    def test_single_parameter_multiple_ranges_second_range(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": [
                        {
                            "operation": MULTIPLY,
                            "value": 3,
                            "range": [300, 400],
                        },
                        {
                            "operation": MULTIPLY,
                            "value": 2,
                            "range": [400, 500],
                        },
                    ]
                }
            },
        )()

        data = {
            "pm10": 450,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 900,
        }

    # --------------------------------------------------------
    # Multiple parameters + multiple ranges
    # --------------------------------------------------------

    def test_multiple_parameters_each_with_multiple_ranges(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": [
                        {
                            "operation": MULTIPLY,
                            "value": 3,
                            "range": [300, 400],
                        },
                        {
                            "operation": MULTIPLY,
                            "value": 2,
                            "range": [400, 500],
                        },
                    ],
                    "pm25": [
                        {
                            "operation": DIVIDE,
                            "value": 2,
                            "range": [0, 50],
                        },
                        {
                            "operation": DIVIDE,
                            "value": 4,
                            "range": [50, 100],
                        },
                    ],
                }
            },
        )()

        data = {
            "pm10": 450,
            "pm25": 80,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 900,
            "pm25": 20,
        }

    # --------------------------------------------------------
    # Missing fields
    # --------------------------------------------------------

    def test_calibration_for_missing_field_is_ignored(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    },
                    "pm25": {
                        "operation": MULTIPLY,
                        "value": 2,
                    },
                }
            },
        )()

        data = {
            "pm10": 100,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": 300,
        }

    # --------------------------------------------------------
    # None values
    # --------------------------------------------------------

    def test_none_value_is_not_calibrated(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    }
                }
            },
        )()

        data = {
            "pm10": None,
        }

        result = apply_device_calibration(device_info, data)

        assert result == {
            "pm10": None,
        }

    # --------------------------------------------------------
    # Other fields remain unchanged
    # --------------------------------------------------------

    def test_unconfigured_fields_remain_unchanged(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    }
                }
            },
        )()

        data = {
            "pm10": 100,
            "pm25": 50,
            "temperature": 25,
            "humidity": 60,
        }

        result = apply_device_calibration(device_info, data)

        assert result["pm10"] == 300
        assert result["pm25"] == 50
        assert result["temperature"] == 25
        assert result["humidity"] == 60

    # --------------------------------------------------------
    # Function mutates original dictionary
    # --------------------------------------------------------

    def test_original_data_dictionary_is_mutated(self):
        device_info = type(
            "DeviceInfo",
            (),
            {
                "calibration_factors": {
                    "pm10": {
                        "operation": MULTIPLY,
                        "value": 3,
                    }
                }
            },
        )()

        data = {
            "pm10": 100,
        }

        result = apply_device_calibration(device_info, data)

        assert result is data
        assert data["pm10"] == 300
