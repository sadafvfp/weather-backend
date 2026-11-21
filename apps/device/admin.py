from django.contrib import admin
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django import forms

import xlsxwriter
from io import BytesIO

from .models import DeviceInfo


def export_as_excel(modeladmin, request, queryset):
    model = modeladmin.model
    if "apply" in request.POST:
        selected_fields = request.POST.getlist("columns")
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet()

        header_format = workbook.add_format({"bold": True, "bg_color": "#D9E1F2"})
        field_labels = {f.name: str(f.verbose_name) for f in model._meta.fields}

        # Write headers
        for col_idx, field in enumerate(selected_fields):
            label = field_labels.get(field, field)
            worksheet.write(0, col_idx, label, header_format)

        # Write rows
        for row_idx, obj in enumerate(queryset, start=1):
            for col_idx, field in enumerate(selected_fields):
                value = getattr(obj, field, "")
                worksheet.write(row_idx, col_idx, str(value))

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="export.xlsx"'
        return response

    # Show intermediate column-selection page
    all_fields = [f.name for f in modeladmin.model._meta.fields]
    return TemplateResponse(
        request,
        "admin/export_columns.html",
        {
            "queryset": queryset,
            "fields": all_fields,
            "action_name": "export_as_excel",
            "opts": modeladmin.model._meta,
        },
    )


export_as_excel.short_description = "Export selected as Excel"


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = DeviceInfo
        fields = "__all__"


class DeviceModelAdmin(admin.ModelAdmin):
    actions = [export_as_excel]
    list_display = (
        "id",
        "device_id",
        "station_name",
        "province",
        "city",
        "status",
        "slug",
    )
    search_fields = (
        "device_id",
        "station_name",
        "province",
        "city",
    )
    list_filter = ("status",)


admin.site.register(DeviceInfo, DeviceModelAdmin)
