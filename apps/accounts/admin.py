from django.contrib import admin
from django.contrib.auth.models import Permission


from .models import User


# Register your models here.
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "content_type")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")


class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "is_superuser")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email")

admin.site.register(User, UserAdmin)