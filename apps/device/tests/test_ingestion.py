# tests/test_ingestion.py

from datetime import timedelta

import pytest
from django.utils import timezone
from unittest.mock import Mock

from backend.apps.device.models import (
    Device,
    LatestData,
    DeviceType,
    SubDevice,
    SubDeviceType,
)
from backend.apps.device.services import (
    LatestDataService,
    IngestionService,
)
from backend.apps.device.models import DataStatus, DeviceStatus, Granularity


from backend.apps.device.services import HistoryDataService


@pytest.fixture
def main_device_type(db):
    return DeviceType.objects.create(
        name="SAPA",
        commercial_name="SAPA",
    )


@pytest.fixture
def info(db, main_device_type):
    return Device.objects.create(
        device_id=136,
        device_type=main_device_type,
        status=DeviceStatus.PRODUCTION,
        is_opm=False,
        forwards_to_municipality=False,
    )


@pytest.fixture
def sub_device_type(db):
    return SubDeviceType.objects.create(
        name="Kit",
        commercial_name="Kit",
    )


@pytest.fixture
def sub_info(db, info, sub_device_type):
    return SubDevice.objects.create(
        device_type=sub_device_type,
        parent=info,
        status=DeviceStatus.PRODUCTION,
    )


class TestLatestDataService:
    @pytest.mark.django_db
    def test_first_reading_is_accepted(self, info):
        now = timezone.now()

        payload = {
            "device_id": 136,
            "pm10": 20.0,
            "pm25": 10.0,
            "created_datetime": now,
        }

        accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
            device_info=info,
            status=DataStatus.PRODUCTION,
            payload=payload,
            min_gap=timedelta(minutes=3),
        )

        assert accepted is True
        assert prev_dt is None
        assert prev_data is None

        row = LatestData.objects.get(
            device_id=info.id,
            status=DataStatus.PRODUCTION,
            granularity=0,
        )

        assert row.created_datetime == now
        assert row.data["pm10"] == 20.0
        assert row.data["pm25"] == 10.0


@pytest.mark.django_db
def test_existing_reading_less_than_min_gap_is_rejected(info):
    previous = timezone.now()

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.PRODUCTION,
        granularity=0,
        created_datetime=previous,
        data={
            "device_id": 136,
            "pm10": 20,
        },
    )

    new_time = previous + timedelta(minutes=2)

    accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
        device_info=info,
        status=DataStatus.PRODUCTION,
        payload={
            "device_id": 136,
            "pm10": 30,
            "created_datetime": new_time,
        },
        min_gap=timedelta(minutes=3),
    )

    assert accepted is False
    assert prev_dt is None
    assert prev_data is None

    row = LatestData.objects.get(
        device_id=info.id,
        status=DataStatus.PRODUCTION,
        granularity=0,
    )

    assert row.created_datetime == previous
    assert row.data["pm10"] == 20


@pytest.mark.django_db
def test_reading_exactly_min_gap_is_accepted(info):
    previous = timezone.now()

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.PRODUCTION,
        granularity=0,
        created_datetime=previous,
        data={"pm10": 20},
    )

    new_time = previous + timedelta(minutes=3)

    accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
        device_info=info,
        status=DataStatus.PRODUCTION,
        payload={
            "device_id": 136,
            "pm10": 30,
            "created_datetime": new_time,
        },
        min_gap=timedelta(minutes=3),
    )

    assert accepted is True
    assert prev_dt == previous
    assert prev_data == {"pm10": 20}

    row = LatestData.objects.get(
        device_id=info.id,
        status=DataStatus.PRODUCTION,
        granularity=0,
    )

    assert row.created_datetime == new_time
    assert row.data["pm10"] == 30


@pytest.mark.django_db
def test_suspicious_and_production_have_independent_latest_rows(info):
    now = timezone.now()

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.PRODUCTION,
        granularity=0,
        created_datetime=now,
        data={"pm10": 20},
    )

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.SUSPICIOUS,
        granularity=0,
        created_datetime=now,
        data={"pm10": 5000},
    )

    assert (
        LatestData.objects.filter(
            device_id=info.id,
            granularity=0,
            status=DataStatus.PRODUCTION,
        ).count()
        == 1
    )

    assert (
        LatestData.objects.filter(
            device_id=info.id,
            granularity=0,
            status=DataStatus.SUSPICIOUS,
        ).count()
        == 1
    )


class TestIngestionService:
    @pytest.mark.django_db
    def test_test_device_gets_test_status(self, info):

        now = timezone.now()

        payload = {
            "device_id": 136,
            "pm10": 20.0,
            "pm25": 10.0,
            "created_datetime": now,
        }
        info.status = DeviceStatus.TEST
        print(info.status)

        accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
            device_info=info,
            status=DataStatus.TEST,
            payload=payload,
            min_gap=timedelta(minutes=1),
        )

        assert accepted is True
        assert prev_dt is None
        assert prev_data is None

        row = LatestData.objects.get(
            device_id=info.id,
            status=DataStatus.TEST,
            granularity=0,
        )

        assert row.created_datetime == now
        assert row.data["pm10"] == 20.0
        assert row.data["pm25"] == 10.0
        # assert result["status"] == DataStatus.TEST
        # assert result["_prev_datetime"] is None
        # assert result["_prev_data"] is None

    def test_out_of_range_production_becomes_suspicious(self, info):
        now = timezone.now()

        # mocker.patch(
        #     "backend.apps.device.services.timezone.now",
        #     return_value=now,
        # )

        info = info
        # info.id = info.id
        # info.device_id = 136
        info.status = DeviceStatus.PRODUCTION

        payload = {
            "device_id": 136,
            "pm10": 99999,
            "pm25": 20,
            "created_datetime": now,
        }

        result = IngestionService.prepare_reading(
            info,
            payload,
            min_gap_map={
                DataStatus.PRODUCTION: timedelta(minutes=3),
                DataStatus.SUSPICIOUS: timedelta(minutes=3),
            },
            sensor_threshold={
                "pm10": (0, 100),
                "pm25": (0, 100),
            },
        )

        assert result["status"] == DataStatus.SUSPICIOUS


@pytest.mark.django_db
def test_suspicious_reading_less_than_suspicious_min_gap_is_rejected(info):
    previous = timezone.now()

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.SUSPICIOUS,
        granularity=0,
        created_datetime=previous,
        data={"pm10": 5000},
    )

    accepted, _, _ = LatestDataService.try_accept_and_store(
        device_info=info,
        status=DataStatus.SUSPICIOUS,
        payload={
            "device_id": 136,
            "pm10": 6000,
            "created_datetime": previous + timedelta(minutes=1),
        },
        min_gap=timedelta(minutes=3),
    )

    assert accepted is False

    row = LatestData.objects.get(
        device_id=info.id,
        status=DataStatus.SUSPICIOUS,
        granularity=0,
    )

    assert row.data["pm10"] == 5000


@pytest.mark.django_db
def test_test_reading_less_than_test_min_gap_is_rejected(info):
    previous = timezone.now()

    LatestData.objects.create(
        device_id=info.id,
        status=DataStatus.TEST,
        granularity=0,
        created_datetime=previous,
        data={"pm10": 20},
    )

    accepted, _, _ = LatestDataService.try_accept_and_store(
        device_info=info,
        status=DataStatus.TEST,
        payload={
            "device_id": 136,
            "pm10": 30,
            "created_datetime": previous + timedelta(minutes=1),
        },
        min_gap=timedelta(minutes=3),
    )

    assert accepted is False


class FakeModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_interpolation_creates_correct_timestamps():

    previous_data = {
        "device_id": 136,
        "pm10": 10.0,
        "pm25": 20.0,
    }

    new_data = {
        "device_id": 136,
        "pm10": 40.0,
        "pm25": 50.0,
    }

    start = timezone.datetime(
        2026,
        9,
        17,
        10,
        0,
        tzinfo=timezone.get_current_timezone(),
    )

    end = start + timedelta(minutes=9)

    rows = HistoryDataService._interpolate(
        FakeModel,
        previous_data,
        new_data,
        start,
        end,
        timedelta(minutes=3),
    )

    assert len(rows) == 2

    assert rows[0].created_datetime == start + timedelta(minutes=3)
    assert rows[1].created_datetime == start + timedelta(minutes=6)

    assert rows[0].is_interpolated is True
    assert rows[1].is_interpolated is True

    assert rows[0].status == DataStatus.PRODUCTION
    assert rows[1].status == DataStatus.PRODUCTION


def test_interpolation_values_are_correct():

    previous_data = {
        "device_id": 136,
        "pm10": 10.0,
        "pm25": 20.0,
    }

    new_data = {
        "device_id": 136,
        "pm10": 40.0,
        "pm25": 50.0,
    }

    start = timezone.now()
    end = start + timedelta(minutes=9)

    rows = HistoryDataService._interpolate(
        FakeModel,
        previous_data,
        new_data,
        start,
        end,
        timedelta(minutes=3),
    )

    assert rows[0].pm10 == pytest.approx(20.0)
    assert rows[1].pm10 == pytest.approx(30.0)

    assert rows[0].pm25 == pytest.approx(30.0)
    assert rows[1].pm25 == pytest.approx(40.0)
    print(rows)


def test_interpolation_does_not_interpolate_metadata():

    previous_data = {
        "device_id": 136,
        "pm10": 10.0,
    }

    new_data = {
        "device_id": 136,
        "pm10": 40.0,
    }

    start = timezone.now()
    end = start + timedelta(minutes=9)

    rows = HistoryDataService._interpolate(
        FakeModel,
        previous_data,
        new_data,
        start,
        end,
        timedelta(minutes=3),
    )

    for row in rows:
        assert row.device_id == 136
        assert row.status == DataStatus.PRODUCTION
        assert row.is_interpolated is True


from django.apps import apps


@pytest.mark.django_db
def test_suspicious_data_does_not_interpolate(mocker):
    SAPA = apps.get_model("device", "SAPA")
    mock_bulk_create = mocker.patch.object(
        SAPA.objects,
        "bulk_create",
    )

    previous_data = {
        "device_id": 136,
        "pm10": 10.0,
    }

    new_data = {
        "device_id": 136,
        "pm10": 5000.0,
        "created_datetime": timezone.now(),
    }

    HistoryDataService.store_reading(
        "SAPA",
        True,
        DataStatus.SUSPICIOUS,
        new_data,
        prev_dt=timezone.now() - timedelta(minutes=30),
        prev_data=previous_data,
    )
    print(mock_bulk_create.call_args)


@pytest.mark.django_db
def test_test_data_does_not_interpolate(mocker):
    SAPA = apps.get_model("device", "SAPA")
    mock_bulk_create = mocker.patch.object(
        SAPA.objects,
        "bulk_create",
    )

    previous_data = {
        "device_id": 136,
        "pm10": 10.0,
    }

    new_data = {
        "device_id": 136,
        "pm10": 20.0,
        "created_datetime": timezone.now(),
    }

    HistoryDataService.store_reading(
        "SAPA",
        True,
        DataStatus.TEST,
        new_data,
        prev_dt=timezone.now() - timedelta(minutes=30),
        prev_data=previous_data,
    )
    print(mock_bulk_create.call_args)

    # args = FakeModel.objects.bulk_create.call_args
    # rows = args.args[0]

    # assert len(rows) == 1
    # assert rows[0].is_interpolated is False


@pytest.mark.django_db
def test_gap_greater_than_max_gap_does_not_interpolate(mocker):
    SAPA = apps.get_model("device", "SAPA")
    mock_bulk_create = mocker.patch.object(
        SAPA.objects,
        "bulk_create",
    )

    previous = timezone.now()
    new = previous + timedelta(hours=5)

    new_data = {
        "device_id": 136,
        "pm10": 100,
        "created_datetime": new,
    }

    HistoryDataService.store_reading(
        "SAPA",
        True,
        DataStatus.PRODUCTION,
        new_data,
        prev_dt=previous,
        prev_data={
            "device_id": 136,
            "pm10": 10,
        },
        interval=timedelta(minutes=3),
        max_gap=timedelta(hours=4),
    )
    print(mock_bulk_create.call_args)

    # rows = FakeModel.objects.bulk_create.call_args.args[0]

    # assert len(rows) == 1
    # assert rows[0].is_interpolated is False


@pytest.mark.django_db
def test_exactly_four_hours_gap(mocker):
    SAPA = apps.get_model("device", "SAPA")
    mock_bulk_create = mocker.patch.object(
        SAPA.objects,
        "bulk_create",
    )

    previous = timezone.now()
    new = previous + timedelta(hours=4)

    new_data = {
        "device_id": 136,
        "pm10": 100,
        "created_datetime": new,
    }

    HistoryDataService.store_reading(
        "SAPA",
        True,
        DataStatus.PRODUCTION,
        new_data,
        prev_dt=previous,
        prev_data={
            "device_id": 136,
            "pm10": 10,
        },
        interval=timedelta(minutes=3),
        max_gap=timedelta(hours=4),
    )
    print(mock_bulk_create.call_args)


@pytest.mark.django_db
def test_less_than_four_hours_gap(mocker):
    SAPA = apps.get_model("device", "SAPA")
    mock_bulk_create = mocker.patch.object(
        SAPA.objects,
        "bulk_create",
    )

    previous = timezone.now()
    new = previous + timedelta(hours=3)

    new_data = {
        "device_id": 136,
        "pm10": 100,
        "created_datetime": new,
    }

    HistoryDataService.store_reading(
        "SAPA",
        True,
        DataStatus.PRODUCTION,
        new_data,
        prev_dt=previous,
        prev_data={
            "device_id": 136,
            "pm10": 10,
        },
        interval=timedelta(minutes=3),
        max_gap=timedelta(hours=4),
    )
    print(mock_bulk_create.call_args)
    # rows = FakeModel.objects.bulk_create.call_args.args[0]

    # If your business rule is "up to 4 hours", this should be > 1.
    # assert len(rows) > 1


class TestLatestDataServiceSubDevice:

    @pytest.mark.django_db
    def test_first_sub_device_reading_is_accepted(self, sub_info):
        now = timezone.now()

        payload = {
            "device_id": 136,
            "pm10": 20.0,
            "pm25": 10.0,
            "created_datetime": now,
        }

        accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
            device_info=sub_info,
            status=DataStatus.PRODUCTION,
            payload=payload,
            min_gap=timedelta(minutes=3),
        )

        assert accepted is True
        assert prev_dt is None
        assert prev_data is None

        row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
        )

        assert row.device is None
        assert row.sub_device == sub_info
        assert row.created_datetime == now
        assert row.data["pm10"] == 20.0
        assert row.data["pm25"] == 10.0

    @pytest.mark.django_db
    def test_existing_sub_device_reading_less_than_min_gap_is_rejected(self, sub_info):
        previous = timezone.now()

        LatestData.objects.create(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=previous,
            data={
                "device_id": 136,
                "pm10": 20,
            },
        )

        new_time = previous + timedelta(minutes=2)

        accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
            device_info=sub_info,
            status=DataStatus.PRODUCTION,
            payload={
                "device_id": 136,
                "pm10": 30,
                "created_datetime": new_time,
            },
            min_gap=timedelta(minutes=3),
        )

        assert accepted is False
        assert prev_dt is None
        assert prev_data is None

        row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
        )

        assert row.device is None
        assert row.data["pm10"] == 20
        assert row.created_datetime == previous

    @pytest.mark.django_db
    def test_sub_device_reading_exactly_min_gap_is_accepted(self, sub_info):
        previous = timezone.now()

        LatestData.objects.create(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=previous,
            data={"pm10": 20},
        )

        new_time = previous + timedelta(minutes=3)

        accepted, prev_dt, prev_data = LatestDataService.try_accept_and_store(
            device_info=sub_info,
            status=DataStatus.PRODUCTION,
            payload={
                "device_id": 136,
                "pm10": 30,
                "created_datetime": new_time,
            },
            min_gap=timedelta(minutes=3),
        )

        assert accepted is True
        assert prev_dt == previous
        assert prev_data == {"pm10": 20}

        row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
        )

        assert row.device is None
        assert row.sub_device == sub_info
        assert row.created_datetime == new_time
        assert row.data["pm10"] == 30

    @pytest.mark.django_db
    def test_suspicious_and_production_have_independent_sub_device_rows(self, sub_info):
        now = timezone.now()

        LatestData.objects.create(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=now,
            data={"pm10": 20},
        )

        LatestData.objects.create(
            sub_device=sub_info,
            status=DataStatus.SUSPICIOUS,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=now,
            data={"pm10": 5000},
        )

        assert (
            LatestData.objects.filter(
                sub_device=sub_info,
                status=DataStatus.PRODUCTION,
                granularity=Granularity.THREE_MINUTE,
            ).count()
            == 1
        )

        assert (
            LatestData.objects.filter(
                sub_device=sub_info,
                status=DataStatus.SUSPICIOUS,
                granularity=Granularity.THREE_MINUTE,
            ).count()
            == 1
        )

        assert (
            LatestData.objects.filter(
                sub_device=sub_info,
                device__isnull=True,
            ).count()
            == 2
        )


class TestIngestionServiceSubDevice:

    @pytest.mark.django_db
    def test_test_sub_device_gets_test_status(self, sub_info):
        now = timezone.now()

        sub_info.status = DeviceStatus.TEST
        sub_info.save(update_fields=["status"])

        payload = {
            "device_id": 136,
            "pm10": 20.0,
            "pm25": 10.0,
            "created_datetime": now,
        }

        result = IngestionService.prepare_reading(
            sub_info,
            payload,
            min_gap_map={
                DataStatus.TEST: timedelta(minutes=3),
            },
        )

        assert result["status"] == DataStatus.TEST

        row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.TEST,
            granularity=Granularity.THREE_MINUTE,
        )

        assert row.device is None
        assert row.sub_device == sub_info
        assert row.data["pm10"] == 20.0
        assert row.data["pm25"] == 10.0

    @pytest.mark.django_db
    def test_out_of_range_sub_device_production_becomes_suspicious(self, sub_info):
        sub_info.status = DeviceStatus.PRODUCTION
        sub_info.save(update_fields=["status"])

        payload = {
            "device_id": 136,
            "pm10": 99999,
            "pm25": 20,
        }

        result = IngestionService.prepare_reading(
            sub_info,
            payload,
            min_gap_map={
                DataStatus.PRODUCTION: timedelta(minutes=3),
                DataStatus.SUSPICIOUS: timedelta(minutes=3),
            },
            sensor_threshold={
                "pm10": (0, 100),
                "pm25": (0, 100),
            },
        )

        assert result["status"] == DataStatus.SUSPICIOUS

        row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.SUSPICIOUS,
            granularity=Granularity.THREE_MINUTE,
        )

        assert row.device is None
        assert row.sub_device == sub_info
        assert row.data["pm10"] == 99999

    @pytest.mark.django_db
    def test_device_and_sub_device_have_independent_latest_rows(self, info, sub_info):
        now = timezone.now()

        # Parent device
        LatestData.objects.create(
            device=info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=now,
            data={"pm10": 10},
        )

        # Sub-device
        LatestData.objects.create(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
            created_datetime=now,
            data={"pm10": 20},
        )

        assert (
            LatestData.objects.filter(
                device=info,
                status=DataStatus.PRODUCTION,
                granularity=Granularity.THREE_MINUTE,
            ).count()
            == 1
        )

        assert (
            LatestData.objects.filter(
                sub_device=sub_info,
                status=DataStatus.PRODUCTION,
                granularity=Granularity.THREE_MINUTE,
            ).count()
            == 1
        )

        parent_row = LatestData.objects.get(
            device=info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
        )

        sub_row = LatestData.objects.get(
            sub_device=sub_info,
            status=DataStatus.PRODUCTION,
            granularity=Granularity.THREE_MINUTE,
        )

        assert parent_row.data["pm10"] == 10
        assert sub_row.data["pm10"] == 20
