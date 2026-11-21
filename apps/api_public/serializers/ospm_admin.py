from rest_framework import serializers


class OSPMThreeMinuteDeleteSerializer(serializers.Serializer):
    created_datetime = serializers.DateTimeField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    datetimes = serializers.ListField(
        child=serializers.DateTimeField(), required=False, allow_empty=False
    )

    def validate(self, attrs):
        modes = 0
        if attrs.get("created_datetime") is not None:
            modes += 1
        if attrs.get("start_date") is not None or attrs.get("end_date") is not None:
            modes += 1
        if attrs.get("datetimes"):
            modes += 1

        if modes != 1:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Specify exactly one deletion mode: created_datetime, "
                        "start_date with end_date, or datetimes."
                    )
                }
            )

        if attrs.get("start_date") is not None or attrs.get("end_date") is not None:
            if attrs.get("start_date") is None or attrs.get("end_date") is None:
                raise serializers.ValidationError(
                    {"detail": "Both start_date and end_date are required for range deletion."}
                )

        return attrs
