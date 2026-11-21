import pytest


from device.models import LatestData, DataStatusFlag


@pytest.mark.django_db
def test_sapa_first_reading_end_to_end(
    api_client,
    mocker,
    sapa_info,
):
    mocker.patch("device.views.history_data_store.delay")

    mocker.patch("device.views.forward_reading_to_municipality.delay")

    response = api_client.post(
        "/aqs/SAPA/",
        {
            "device_id": sapa_info.device_id,
            "pm10": 30,
            "pm25": 10,
            "so2": 20,
            "no2": 30,
            "o3": 40,
            "co": 50,
            "temperature": 25,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data == "Done"

    latest = LatestData.objects.get(
        device=sapa_info,
        status=DataStatusFlag.PRODUCTION,
        granularity=0,
    )

    assert latest.data["pm10"] == 30


@pytest.mark.django_db
def test_rejected_reading_does_not_enqueue_history(
    api_client,
    sapa_info,
    mocker,
):
    now = timezone.now()

    LatestData.objects.create(
        device=sapa_info,
        status=DataStatusFlag.PRODUCTION,
        granularity=0,
        created_datetime=now,
        data={"pm10": 20},
    )

    history_delay = mocker.patch("device.views.history_data_store.delay")

    forward_delay = mocker.patch("device.views.forward_reading_to_municipality.delay")

    # You need to patch timezone.now in the module where it is used
    mocker.patch(
        "device.services.timezone.now",
        return_value=now + timedelta(minutes=1),
    )

    response = api_client.post(
        "/aqs/SAPA/",
        {
            "device_id": sapa_info.device_id,
            "pm10": 30,
            "pm25": 10,
            "so2": 20,
            "no2": 30,
            "o3": 40,
            "co": 50,
        },
        format="json",
    )

    assert response.status_code != 200

    history_delay.assert_not_called()
    forward_delay.assert_not_called()


@pytest.mark.django_db
def test_municipality_is_enqueued_when_enabled(
    api_client,
    sapa_info,
    mocker,
):
    sapa_info.forwards_to_municipality = True
    sapa_info.save(update_fields=["forwards_to_municipality"])

    forward = mocker.patch("device.views.forward_reading_to_municipality.delay")

    mocker.patch("device.views.history_data_store.delay")

    response = api_client.post(
        "/aqs/SAPA/",
        {
            "device_id": sapa_info.device_id,
            "pm10": 30,
            "pm25": 10,
            "so2": 20,
            "no2": 30,
            "o3": 40,
            "co": 50,
        },
        format="json",
    )

    assert response.status_code == 200
    forward.assert_called_once()


@pytest.mark.django_db
def test_municipality_is_not_enqueued_when_disabled(
    api_client,
    sapa_info,
    mocker,
):
    sapa_info.forwards_to_municipality = False
    sapa_info.save(update_fields=["forwards_to_municipality"])

    forward = mocker.patch("device.views.forward_reading_to_municipality.delay")

    mocker.patch("device.views.history_data_store.delay")

    response = api_client.post(
        "/aqs/SAPA/",
        {
            "device_id": sapa_info.device_id,
            "pm10": 30,
            "pm25": 10,
            "so2": 20,
            "no2": 30,
            "o3": 40,
            "co": 50,
        },
        format="json",
    )

    assert response.status_code == 200
    forward.assert_not_called()


@pytest.mark.django_db
def test_deactivated_device_is_rejected(
    api_client,
    sapa_info,
):
    sapa_info.status = DeviceStatusFlag.DEACTIVATED
    sapa_info.save(update_fields=["status"])

    response = api_client.post(
        "/aqs/SAPA/",
        {
            "device_id": sapa_info.device_id,
            "pm10": 30,
        },
        format="json",
    )

    assert response.status_code == 403


def test_ingestion_uses_server_time_for_created_datetime(
    mocker,
):
    now = timezone.now()

    mocker.patch(
        "device.services.timezone.now",
        return_value=now,
    )

    info = Mock()
    info.id = 1
    info.device_id = 136
    info.status = DeviceStatusFlag.TEST

    result = IngestionService.prepare_reading(
        info,
        {
            "pm10": 20,
        },
        min_gap_map={
            DataStatusFlag.TEST: timedelta(minutes=3),
        },
    )

    assert result["created_datetime"] == timezone.localtime(now)
