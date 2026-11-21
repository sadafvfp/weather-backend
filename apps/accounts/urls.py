from django.urls import path

from .views import (
    ChangePasswordView,
    ProfileView,
    RegisterView,
    ResetPasswordView,
    UserDetailView,
    # UserDeviceView,
    UserListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="accounts-register"),
    path("profile/", ProfileView.as_view(), name="accounts-profile"),
    path(
        "password/change/",
        ChangePasswordView.as_view(),
        name="accounts-change-password",
    ),
    path("users/", UserListView.as_view(), name="accounts-user-list"),
    path("users/<uuid:uuid>/", UserDetailView.as_view(), name="accounts-user-detail"),
    # path(
    #     "users/<uuid:uuid>/devices/",
    #     UserDeviceView.as_view(),
    #     name="accounts-user-devices",
    # ),
    path(
        "users/<uuid:uuid>/reset-password/",
        ResetPasswordView.as_view(),
        name="accounts-reset-password",
    ),
]
