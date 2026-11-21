MULTIPLY = "*"
DIVIDE = "/"


def apply_calibration_rule(value, rule):

    if rule is None:
        return value

    # Simple rule or conditional single rule
    if isinstance(rule, dict):
        rules = [rule]

    # Multiple conditional rules
    elif isinstance(rule, list):
        rules = rule

    # Simple numeric factor
    else:
        return value * float(rule)

    for sub_rule in rules:
        value_range = sub_rule.get("range")

        # If a range exists, only apply the rule inside that range
        if value_range is not None:
            min_value, max_value = value_range

            if not min_value <= value < max_value:
                continue

        operation = sub_rule.get("operation", MULTIPLY)
        factor = float(sub_rule["value"])

        if operation == MULTIPLY:
            return value * factor

        if operation == DIVIDE:
            return value / factor

        raise ValueError(f"Unsupported calibration operation: {operation}")

    # No rule matched the value
    return value


def apply_device_calibration(device_info, data):
    factors = device_info.calibration_factors or {}

    for field, rule in factors.items():
        value = data.get(field)
        if value is not None:
            data[field] = apply_calibration_rule(value, rule)

    return data
