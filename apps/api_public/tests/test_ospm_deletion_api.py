from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.device.models import DataStatus, DeviceInfo, Granularity, LatestData, OSPM

User = get_user_model()


@pytest.fixture
def device(db):
    return DeviceInfo.objects.create(
        device_id=700,
        province="تهران",
        city="تهران",
        station_name="حذف API",
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="admin-del",
        email="admin-del@example.com",
        password="pass12345!",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="user-del",
        email="user-del@example.com",
        password="pass12345!",
    )


@pytest.mark.django_db
def test_non_admin_cannot_delete_ospm_rows(device, regular_user):
    client = APIClient()
    client.force_authenticate(user=regular_user)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/?status=0",
        {"created_datetime": timezone.now().isoformat()},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
@patch("backend.apps.api_public.views.ospm_admin.refresh_ospm_continuous_aggregates.delay")
def test_superuser_deletes_single_row_and_queues_refresh(delay, device, superuser):
    tz = timezone.get_current_timezone()
    bucket = timezone.make_aware(timezone.datetime(2026, 6, 1, 8, 3, 0), tz)
    OSPM.objects.create(
        created_datetime=bucket,
        device_id=device.device_id,
        pm10=1,
        pm25=1,
        temperature=1,
        humidity=1,
        status=DataStatus.PRODUCTION,
    )
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/?status=0",
        {"created_datetime": (bucket + timedelta(minutes=2)).isoformat()},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
    assert response.json()["aggregate_refresh"] == "pending"
    delay.assert_called_once()
    assert OSPM.objects.filter(device_id=device.device_id).count() == 0


@pytest.mark.django_db
@patch("backend.apps.api_public.views.ospm_admin.refresh_ospm_continuous_aggregates.delay")
def test_delete_test_status_skips_cagg_refresh(delay, device, superuser):
    tz = timezone.get_current_timezone()
    bucket = timezone.make_aware(timezone.datetime(2026, 6, 2, 8, 3, 0), tz)
    OSPM.objects.create(
        created_datetime=bucket,
        device_id=device.device_id,
        pm10=1,
        pm25=1,
        temperature=1,
        humidity=1,
        status=DataStatus.TEST,
    )
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/?status=1",
        {"created_datetime": bucket.isoformat()},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
    assert response.json()["aggregate_refresh"] == "skipped"
    delay.assert_not_called()


@pytest.mark.django_db
@patch("backend.apps.api_public.views.ospm_admin.refresh_ospm_continuous_aggregates.delay")
def test_range_delete_both_statuses_refreshes_when_production_present(
    delay, device, superuser
):
    tz = timezone.get_current_timezone()
    t1 = timezone.make_aware(timezone.datetime(2026, 7, 1, 8, 0, 0), tz)
    t2 = timezone.make_aware(timezone.datetime(2026, 7, 1, 8, 3, 0), tz)
    OSPM.objects.create(
        created_datetime=t1,
        device_id=device.device_id,
        pm10=1,
        pm25=1,
        temperature=1,
        humidity=1,
        status=DataStatus.PRODUCTION,
    )
    OSPM.objects.create(
        created_datetime=t2,
        device_id=device.device_id,
        pm10=1,
        pm25=1,
        temperature=1,
        humidity=1,
        status=DataStatus.TEST,
    )
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/?status=10",
        {"start_date": t1.isoformat(), "end_date": t2.isoformat()},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert response.json()["aggregate_refresh"] == "pending"
    delay.assert_called_once()


@pytest.mark.django_db
def test_delete_requires_status_query_param(device, superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/",
        {"created_datetime": timezone.now().isoformat()},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_delete_requires_explicit_criteria(device, superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(
        f"/kwz/admin/ospm/{device.device_id}/three-minute/delete/",
        {},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
@patch("backend.apps.device.signals.refresh_ospm_continuous_aggregates.delay")
def test_deleting_device_info_deletes_latest_and_history_and_refreshes_caggs(
    delay, device, superuser
):
    tz = timezone.get_current_timezone()
    t1 = timezone.make_aware(timezone.datetime(2026, 6, 1, 8, 0, 0), tz)
    t2 = timezone.make_aware(timezone.datetime(2026, 6, 1, 8, 6, 0), tz)
    for ts in (t1, t2):
        OSPM.objects.create(
            created_datetime=ts,
            device_id=device.device_id,
            pm10=1,
            pm25=1,
            temperature=1,
            humidity=1,
            status=DataStatus.PRODUCTION,
        )
    LatestData.objects.create(
        deviceinfo=device,
        status=DataStatus.PRODUCTION,
        granularity=Granularity.THREE_MINUTE,
        created_datetime=t2,
        data={"pm10": 1},
    )

    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.delete(f"/kwz/device-info/{device.slug}/")
    assert response.status_code == 204
    assert not DeviceInfo.objects.filter(device_id=device.device_id).exists()
    assert not LatestData.objects.filter(deviceinfo_id=device.device_id).exists()
    assert not OSPM.objects.filter(device_id=device.device_id).exists()
    delay.assert_called_once_with(t1.isoformat(), t2.isoformat())


@pytest.mark.django_db
def test_updating_device_info_forbids_changing_device_id(device, superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.put(
        f"/kwz/device-info/{device.slug}/",
        {
            "device_id": device.device_id + 1,
            "station_name": device.station_name,
            "city": device.city,
            "province": device.province,
            "status": device.status,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "device_id" in response.json()
