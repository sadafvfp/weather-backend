
from datetime import timedelta
from django.db.models import Avg, Max, Min, TextChoices
from django.core.exceptions import ValidationError
from django.db.models import F
from rest_framework.exceptions import ParseError
from rest_framework.filters import BaseFilterBackend

class BucketOrderingFilter(BaseFilterBackend):
    param = "ordering"
    default = "-created_datetime"
    aliases = {"created_datetime": "bucket"}

    def filter_queryset(self, request, queryset, view):
        raw = request.query_params.get(self.param, self.default).strip()
        desc = raw.startswith("-")
        name = raw[1:] if desc else raw

        column = self.aliases.get(name)
        if column is None:
            if name not in view.measurement_fields:
                allowed = sorted(view.measurement_fields | self.aliases.keys())
                raise ParseError(
                    f"Invalid ordering. Allowed: {', '.join(allowed)} (prefix with - for descending)."
                )
            column = name

        expr = (
            F(column).desc(nulls_last=True) if desc else F(column).asc(nulls_last=True)
        )
        if column == "bucket":
            return queryset.order_by(expr)
        return queryset.order_by(expr, "-bucket")
