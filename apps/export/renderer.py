# import io
# import xlsxwriter
# from rest_framework.renderers import BaseRenderer

# AQI_COLORS = [  # (min, max, background, font)
#     (0, 50, "#00E400", "#000000"),
#     (51, 100, "#FFFF00", "#000000"),
#     (101, 150, "#FF7E00", "#000000"),
#     (151, 200, "#FF0000", "#FFFFFF"),
#     (201, 300, "#8F3F97", "#FFFFFF"),
#     (301, 10000, "#7E0023", "#FFFFFF"),
# ]


# class FastXLSXRenderer(BaseRenderer):
#     media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     format = "xlsx"
#     charset = None
#     render_style = "binary"

#     def _titles(self, view, keys):
#         try:
#             fields = (
#                 view.get_serializer().fields
#             )  # declared fields only, built once per request
#         except Exception:
#             fields = {}
#         titles = []
#         for k in keys:
#             f = fields.get(k)
#             titles.append(str(f.label) if f is not None and f.label else k)
#         return titles

#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         ctx = renderer_context or {}
#         response, view = ctx.get("response"), ctx.get("view")
#         rows = list(data) if data else []

#         if response is not None and response.status_code == 200:
#             name = getattr(view, "filename", "export.xlsx")
#             response["Content-Disposition"] = f'attachment; filename="{name}"'
#         if not rows or not isinstance(rows[0], dict):
#             return b""

#         keys = list(rows[0].keys())
#         buf = io.BytesIO()
#         wb = xlsxwriter.Workbook(buf, {"in_memory": True})
#         ws = wb.add_worksheet("data")
#         # ws.right_to_left()   # uncomment for a right-to-left sheet

#         # formats are created ONCE and reused, so they cost nothing per cell
#         header = wb.add_format(
#             {
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#1F4E78",
#                 "align": "center",
#                 "valign": "vcenter",
#                 "border": 1,
#                 "text_wrap": True,
#             }
#         )
#         text = wb.add_format({"align": "center"})
#         number = wb.add_format({"align": "center", "num_format": "0.00"})
#         integer = wb.add_format({"align": "center", "num_format": "0"})

#         # column formats: applied to every cell in the column that has no own format
#         for col, key in enumerate(keys):
#             if key.endswith("_aqi") or key == "aqi":
#                 fmt, width = integer, 10
#             elif key in ("persian_datetime", "created_datetime", "main_pollutant"):
#                 fmt, width = text, 22 if "datetime" in key else 16
#             else:
#                 fmt, width = number, 12
#             ws.set_column(col, col, width, fmt)

#         ws.set_row(0, 28)
#         ws.write_row(0, 0, self._titles(view, keys), header)

#         for r, row in enumerate(rows, start=1):
#             ws.write_row(r, 0, [row.get(k) for k in keys])  # None -> blank cell

#         last = len(rows)
#         ws.freeze_panes(1, 0)
#         ws.autofilter(0, 0, last, len(keys) - 1)

#         # AQI colors: ONE rule per range, not one style per cell
#         if "aqi" in keys:
#             col = keys.index("aqi")
#             for lo, hi, bg, fg in AQI_COLORS:
#                 ws.conditional_format(
#                     1,
#                     col,
#                     last,
#                     col,
#                     {
#                         "type": "cell",
#                         "criteria": "between",
#                         "minimum": lo,
#                         "maximum": hi,
#                         "format": wb.add_format({"bg_color": bg, "font_color": fg}),
#                     },
#                 )

#         wb.close()
#         return buf.getvalue()


import io
import copy
import xlsxwriter
from rest_framework.renderers import BaseRenderer
from xlsxwriter.utility import xl_rowcol_to_cell

AQI_BANDS = [  # (min, max, background, font)
    (0, 50, "#00E400", "#000000"),
    (51, 100, "#FFFF00", "#000000"),
    (101, 150, "#FF7E00", "#000000"),
    (151, 200, "#FF0000", "#FFFFFF"),
    (201, 300, "#8F3F97", "#FFFFFF"),
    (301, 10000, "#7E0023", "#FFFFFF"),
]

DEFAULT_STYLE = {
    # values in these dicts are plain xlsxwriter format properties
    "header": {
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": "#1F4E78",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "text_wrap": True,
    },
    "text": {"align": "center"},
    "body": {"align": "center", "valign": "vcenter"},
    "number": {"align": "center", "num_format": "0.00"},
    "integer": {"align": "center", "num_format": "0"},
    "legend_title": {
        "bold": True,
        "font_size": 13,
        "align": "center",
        "valign": "vcenter",
        "bg_color": "#D9E1F2",
        "border": 1,
    },
    "legend_range": {"bold": True, "align": "center", "valign": "vcenter", "border": 1},
    "legend_text": {
        "align": "right",
        "valign": "vcenter",
        "text_wrap": True,
        "border": 1,
    },
    "header_height": 28,
    "legend_row_height": 22,
    "default_width": 12,
    "widths": {
        "persian_datetime": 22,
        "created_datetime": 22,
        "main_pollutant": 16,
        "aqi": 10,
    },
    "legend_span": 6,  # how many columns the meaning text is merged across
    "rtl": False,
    "freeze_header": False,
    "autofilter": True,
    "constant_memory": True,
    "sheet_name": "data",
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _order_keys(keys, order):
    """Sort keys by their position in `order`. Keys not listed go last,
    keeping their original relative order (sorted() is stable)."""
    if not order:
        return keys
    rank = {k: i for i, k in enumerate(order)}
    return sorted(keys, key=lambda k: rank.get(k, len(rank)))


def _requested_fields(view):
    request = getattr(view, "request", None)
    raw = request.query_params.get("fields", "") if request else ""
    wanted = {f.strip() for f in raw.split(",") if f.strip()}
    if "error_code" in wanted:
        wanted.discard("error_code")
        wanted.add("error_code_label")
    return wanted


class FastXLSXRenderer(BaseRenderer):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    format = "xlsx"
    charset = None
    render_style = "binary"

    def _titles(self, view, keys):
        try:
            fields = view.get_serializer().fields
        except Exception:
            fields = {}
        return [
            str(fields[k].label) if k in fields and fields[k].label else k for k in keys
        ]

    def render(self, data, accepted_media_type=None, renderer_context=None):
        ctx = renderer_context or {}
        response, view = ctx.get("response"), ctx.get("view")
        rows = list(data) if data else []

        if response is not None and response.status_code == 200:
            name = view.get_filename() or "export.xlsx"
            response["Content-Disposition"] = f'attachment; filename="{name}"'
        if not rows or not isinstance(rows[0], dict):
            return b""

        st = _merge(DEFAULT_STYLE, getattr(view, "excel_style", None))
        legend = getattr(view, "excel_legend", None)  # dict or None
        bands = getattr(view, "excel_color_bands", {})  # {"aqi": AQI_BANDS}

        keys = _order_keys(
            list(rows[0].keys()),
            getattr(view, "excel_column_order", None),
        )
        wanted = _requested_fields(view)
        if wanted:
            always = set(getattr(view, "excel_always_fields", ("persian_datetime",)))
            keys = [k for k in keys if k in wanted or k in always]

        ncols = len(keys)
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(
            buf,
            {
                "in_memory": not st["constant_memory"],
                "constant_memory": st["constant_memory"],
            },
        )
        ws = wb.add_worksheet(st["sheet_name"])
        if st["rtl"]:
            ws.right_to_left()

        f = {
            n: wb.add_format({**st["body"], **st[n]})
            for n in ("text", "number", "integer")
        }
        f.update(
            {
                n: wb.add_format(st[n])
                for n in ("header", "legend_title", "legend_range", "legend_text")
            }
        )

        # column formats and widths
        col_fmts = []
        # col_fmts = [wb.add_format({"border": 1, "align": "center"}) for _ in keys]
        for col, key in enumerate(keys):
            if key == "aqi" or key.endswith("_aqi"):
                kind = "integer"
            elif key in ("persian_datetime", "created_datetime", "main_pollutant"):
                kind = "text"
            else:
                kind = "number"
            props = {**st["body"], **st[kind], **st.get("columns", {}).get(key, {})}
            col_fmts.append(wb.add_format(props))
            # width only: no format here, so empty cells stay unstyled
            ws.set_column(col, col, st["widths"].get(key, st["default_width"]))

        # legend block (rows must be written top to row, in order)
        row = 0
        if legend:
            span_end = min(ncols - 1, st["legend_span"])
            if legend.get("title"):
                ws.merge_range(
                    row, 0, row, span_end, legend["title"], f["legend_title"]
                )
                ws.set_row(row, st["legend_row_height"])
                row += 1
            for rng, meaning, bg, fg in legend.get("rows", []):
                rng_fmt = wb.add_format(
                    {**st["legend_range"], "bg_color": bg, "font_color": fg}
                )
                ws.write(row, 0, rng, rng_fmt)
                if span_end > 1:
                    ws.merge_range(row, 1, row, span_end, meaning, f["legend_text"])
                else:
                    ws.write(row, 1, meaning, f["legend_text"])
                ws.set_row(row, st["legend_row_height"])
                row += 1
            row += 1  # blank spacer row

        header_row = row
        ws.set_row(header_row, st["header_height"])
        ws.write_row(header_row, 0, self._titles(view, keys), f["header"])

        first = header_row + 1
        for i, r in enumerate(rows):
            rr = first + i
            for c, k in enumerate(keys):
                ws.write(rr, c, r.get(k), col_fmts[c])
        last = first + len(rows) - 1

        if st["freeze_header"]:
            ws.freeze_panes(first, 0)
        if st["autofilter"]:
            ws.autofilter(header_row, 0, last, ncols - 1)
        for key, band_list in bands.items():
            if key in keys:
                col = keys.index(key)
                top = xl_rowcol_to_cell(first, col)  # relative ref, e.g. "M5"
                for lo, hi, bg, fg in band_list:
                    ws.conditional_format(
                        first,
                        col,
                        last,
                        col,
                        {
                            "type": "formula",
                            "criteria": f"=AND(ISNUMBER({top}),{top}>={lo},{top}<={hi})",
                            "format": wb.add_format({"bg_color": bg, "font_color": fg}),
                        },
                    )

        wb.close()
        return buf.getvalue()
