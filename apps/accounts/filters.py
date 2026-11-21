import django_filters as filters
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(filters.FilterSet):
    # Exact lookups
    # Text fields: case-insensitive partial match
    username = filters.CharFilter(
        lookup_expr="icontains",
        help_text="Partial match (case-insensitive) on username.",
    )
    email = filters.CharFilter(lookup_expr="icontains")
    first_name = filters.CharFilter(lookup_expr="icontains")
    last_name = filters.CharFilter(lookup_expr="icontains")

    # Booleans
    is_active = filters.BooleanFilter(help_text="Exact match on active status.")
    is_staff = filters.BooleanFilter()
    is_superuser = filters.BooleanFilter(help_text="Exact match on superuser status.")

    # Date ranges: ?date_joined_after=2026-01-01&date_joined_before=2026-06-30
    date_joined = filters.DateFromToRangeFilter(
        help_text=(
            "Inclusive date range on date_joined using date_joined_after and "
            "date_joined_before query params (ISO 8601 date or datetime)."
        ),
    )
    last_login = filters.DateFromToRangeFilter(
        help_text=(
            "Inclusive range on last_login using last_login_after and "
            "last_login_before query params (ISO 8601 date or datetime)."
        ),
    )

    # Datetime precision if you need it: ?date_joined_after=2026-01-01T00:00:00
    date_joined_after = filters.IsoDateTimeFilter(
        field_name="date_joined",
        lookup_expr="gte",
        help_text="date_joined greater than or equal (ISO 8601 datetime).",
    )
    date_joined_before = filters.IsoDateTimeFilter(
        field_name="date_joined",
        lookup_expr="lte",
        help_text="date_joined less than or equal (ISO 8601 datetime).",
    )
    last_login_after = filters.IsoDateTimeFilter(
        field_name="last_login",
        lookup_expr="gte",
        help_text="last_login greater than or equal (ISO 8601 datetime).",
    )
    last_login_before = filters.IsoDateTimeFilter(
        field_name="last_login",
        lookup_expr="lte",
        help_text="last_login less than or equal (ISO 8601 datetime).",
    )

    # Never logged in: ?never_logged_in=true
    never_logged_in = filters.BooleanFilter(
        field_name="last_login",
        lookup_expr="isnull",
        help_text="When true, only users who have never logged in.",
    )

    class Meta:
        model = User
        fields = []  # everything is declared explicitly above
