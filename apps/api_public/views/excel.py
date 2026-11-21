from .history import (
    AirHistoryOnlineListAPIView,
    AirHistoryHourlyListAPIView,
    AirHistoryDailyListAPIView,
    AirHistoryDailyTemperatureListAPIView,
)
from ..serializers.excel import (
    PublicAirSerializer,
    PublicTemperatureSerializer,
    QueryParamSerializer,
)
from backend.apps.export.renderer import FastXLSXRenderer, AQI_BANDS

AQI_LEGEND = {
    "title": "راهنمای شاخص کیفیت هوا (AQI)",
    "rows": [
        ("0 - 50", "هوای پاک؛ آلودگی خطری ایجاد نمی‌کند", "#00E400", "#000000"),
        (
            "51 - 100",
            "قابل قبول؛ برای افراد بسیار حساس ممکن است کمی نگران‌کننده باشد",
            "#FFFF00",
            "#000000",
        ),
        ("101 - 150", "ناسالم برای گروه‌های حساس", "#FF7E00", "#000000"),
        ("151 - 200", "ناسالم برای عموم", "#FF0000", "#FFFFFF"),
        ("201 - 300", "بسیار ناسالم؛ هشدار سلامت برای همه", "#8F3F97", "#FFFFFF"),
        ("301+", "خطرناک؛ وضعیت اضطراری", "#7E0023", "#FFFFFF"),
    ],
}

EXCEL_BODY_STYLE = {
    "border": 1,
    "font_name": "Vazirmatn",
    "font_size": 11,
}

EXCEL_COLUMN_ORDER = [
    "persian_datetime",
    "pm10",
    "pm25",
    "pm10_min",
    "pm10_max",
    "pm25_min",
    "pm25_max",
    "temperature",
    "temperature_min",
    "temperature_max",
    "humidity",
    "flow",
    "error_code_label",
]


def make_excel_style(header_color: str) -> dict:
    return {
        "header": {"bg_color": header_color},
        "body": dict(EXCEL_BODY_STYLE),
    }


class BaseExcelExportMixin:
    """Shared config for all Excel export views. Put it first in the bases."""

    renderer_classes = (FastXLSXRenderer,)
    filename = "my_export.xlsx"
    pagination_class = None
    serializer_queryparams = QueryParamSerializer
    xlsx_use_labels = True
    excel_column_order = EXCEL_COLUMN_ORDER

    def get_filename(self):
        return f"{self.device_info.slug}.xlsx"


class AirExcelMixin(BaseExcelExportMixin):
    """Adds the AQI serializer, legend and color bands."""

    serializer_class = PublicAirSerializer
    excel_legend = AQI_LEGEND
    excel_color_bands = {"aqi": AQI_BANDS}


class AirExcelOnlineListAPIView(AirExcelMixin, AirHistoryOnlineListAPIView):
    excel_style = make_excel_style("#0B5345")


class AirExcelHourlyAPIView(AirExcelMixin, AirHistoryHourlyListAPIView):
    excel_style = make_excel_style("#F0CA22")


class AirExcelDailyAPIView(AirExcelMixin, AirHistoryDailyListAPIView):
    excel_style = make_excel_style("#5523C9")


class AirExcelTemperatureAPIView(
    BaseExcelExportMixin, AirHistoryDailyTemperatureListAPIView
):
    serializer_class = PublicTemperatureSerializer
    excel_style = make_excel_style("#3DA5EB")
