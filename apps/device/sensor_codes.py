from django.conf import settings
from rest_framework.exceptions import ValidationError


def _mapping():
    return getattr(settings, "OSPM_SENSOR_ERROR_CODES", {}) or {}


def parse_error_code(raw):
    """
    Parse ingestion/API ``error_code`` as a single integer.
    Returns None when raw is missing/blank (legacy clients).
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        raise ValidationError({"error_code": "Must be a non-negative integer."})
    if isinstance(raw, int):
        value = raw
    else:
        text = str(raw).strip()
        if not text:
            return None
        if not text.isdigit():
            raise ValidationError({"error_code": "Must be a non-negative integer."})
        value = int(text)
    if value < 0:
        raise ValidationError({"error_code": "Must be a non-negative integer."})
    return value


def normalize_error_code(raw):
    return parse_error_code(raw)


def has_sensor_error(raw):
    code = parse_error_code(raw)
    return code is not None and code != 0


def sensor_error_code_label(raw):
    """Persian-readable label for a single stored error code."""
    code = parse_error_code(raw)
    if code is None or code == 0:
        return None
    mapping = _mapping()
    return mapping.get(code, str(code))


# Backward-compatible aliases for internal call sites during transition.
sensor_code_labels = sensor_error_code_label
parse_sensor_code_string = parse_error_code
normalize_sensor_code_string = normalize_error_code
