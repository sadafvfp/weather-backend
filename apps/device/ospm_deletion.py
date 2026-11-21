from rest_framework.exceptions import ValidationError

from .models import DataStatus

_ALLOWED = frozenset((DataStatus.PRODUCTION, DataStatus.TEST, DataStatus.SUSPICIOUS))
_BOTH_SENTINEL = 10


def parse_deletion_status_param(raw, *, allow_both):
    if raw is None or str(raw).strip() == "":
        raise ValidationError({"status": "This query parameter is required."})

    text = str(raw).strip()
    if allow_both and text == str(_BOTH_SENTINEL):
        return [DataStatus.PRODUCTION, DataStatus.TEST]

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValidationError(
            {"status": "Must be 0, 1, 2, or a comma-separated list (e.g. status=0,2 or status=10)."}
        )

    statuses = []
    seen = set()
    for part in parts:
        if not part.isdigit():
            raise ValidationError(
                {
                    "status": "Must be 0, 1, 2, or a comma-separated list (e.g. status=0,2 or status=10)."
                }
            )
        value = int(part)
        if value not in _ALLOWED:
            raise ValidationError(
                {"status": "Allowed values are 0 (production), 1 (test), and 2 (suspicious)."}
            )
        if value not in seen:
            seen.add(value)
            statuses.append(value)

    if not allow_both:
        if len(statuses) != 1:
            raise ValidationError(
                {"status": "Single-record deletion accepts exactly one status: 0, 1, or 2."}
            )
    elif len(statuses) == 0:
        raise ValidationError(
            {"status": "Must be 0, 1, 2, or a comma-separated list (e.g. status=0,2 or status=10)."}
        )

    return statuses
