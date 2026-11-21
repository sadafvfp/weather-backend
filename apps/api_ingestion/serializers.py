from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers

from ..device.models import OSPM
from ..device.sensor_codes import normalize_error_code, parse_error_code
from ..device.utils import normalize_three_minute_datetime

MAX_BATCH_RECORDS = 500
MAX_FUTURE_SKEW = timedelta(minutes=5)


class ErrorCodeField(serializers.Field):
    default_error_messages = {
        "invalid": "Must be a non-negative integer.",
    }

    def to_internal_value(self, data):
        if data is None or data == "":
            return None
        try:
            parse_error_code(data)
        except serializers.ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict) and "error_code" in detail:
                raise serializers.ValidationError(detail["error_code"])
            raise serializers.ValidationError(detail)
        return normalize_error_code(data)

    def to_representation(self, value):
        return value


# air
class OSPMSerializer(serializers.ModelSerializer):
    error_code = ErrorCodeField(required=False, allow_null=True)
    flow = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = OSPM
        exclude = ["created_datetime", "device_id", "status"]


class OSPMHistoryItemSerializer(serializers.ModelSerializer):
    created_datetime = serializers.DateTimeField(required=True)
    error_code = ErrorCodeField(required=False, allow_null=True, default=0)
    flow = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = OSPM
        fields = [
            "created_datetime",
            "pm10",
            "pm25",
            "temperature",
            "humidity",
            "flow",
            "error_code",
        ]

    def validate_created_datetime(self, value):
        normalized = normalize_three_minute_datetime(value)
        now = timezone.localtime(timezone.now())
        if normalized > now + MAX_FUTURE_SKEW:
            raise serializers.ValidationError("Timestamp cannot be in the future.")
        return normalized


class OSPMBatchIngestionSerializer(serializers.Serializer):
    device_id = serializers.IntegerField(min_value=1)
    total_batch = serializers.IntegerField(min_value=1)
    batch_id = serializers.IntegerField(min_value=1)
    data_h = OSPMHistoryItemSerializer(many=True, required=False, default=list)
    data_s = OSPMHistoryItemSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        if attrs["batch_id"] > attrs["total_batch"]:
            raise serializers.ValidationError(
                {"batch_id": "batch_id cannot be greater than total_batch."}
            )

        data_h = attrs.get("data_h") or []
        data_s = attrs.get("data_s") or []
        total_records = len(data_h) + len(data_s)

        if total_records == 0:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "At least one record in data_h or data_s is required."
                    ]
                }
            )

        if total_records > MAX_BATCH_RECORDS:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        f"Total records across data_h and data_s cannot exceed {MAX_BATCH_RECORDS}."
                    ]
                }
            )

        # Deduplicate by normalized 3-minute timestamp across both lists
        # and ensure data_h and data_s are strictly ordered by created_datetime ASC.
        seen_timestamps = {}
        deduped_h = []
        deduped_s = []

        for item in sorted(data_h, key=lambda r: r["created_datetime"]):
            ts = item["created_datetime"]
            if ts not in seen_timestamps:
                seen_timestamps[ts] = "data_h"
                deduped_h.append(item)

        for item in sorted(data_s, key=lambda r: r["created_datetime"]):
            ts = item["created_datetime"]
            if ts in seen_timestamps:
                if seen_timestamps[ts] == "data_h":
                    raise serializers.ValidationError(
                        {
                            "created_datetime": (
                                f"Timestamp {ts.isoformat()} appears in both data_h and data_s."
                            )
                        }
                    )
                continue
            seen_timestamps[ts] = "data_s"
            deduped_s.append(item)

        attrs["data_h"] = deduped_h
        attrs["data_s"] = deduped_s
        return attrs
