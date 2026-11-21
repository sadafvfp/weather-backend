import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from backend.apps.device.models import (
    DataStatus,
    DeviceInfo,
    DeviceStatus,
    Granularity,
    LatestData,
    OSPM,
)

User = get_user_model()

DEVICE_ID = 500
OSPM_ROW_COUNT = 480 * 3
SUSPICIOUS_COUNT = 500
INTERVAL = timedelta(minutes=3)

CAGG_VIEWS = (
    "hourly_ospm",
    "hourly_ospm_temp",
    "daily_ospm",
    "daily_ospm_temp",
)


def refresh_continuous_aggregates():
    with connection.cursor() as cursor:
        for view in CAGG_VIEWS:
            cursor.execute(
                "CALL refresh_continuous_aggregate(%s, NULL, NULL);",
                [view],
            )


def ensure_superuser():
    if User.objects.filter(username="admin").exists():
        return False
    User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password@123",
    )
    return True


def ensure_device_info():
    device, created = DeviceInfo.objects.update_or_create(
        device_id=DEVICE_ID,
        defaults={
            "station_name": "هواشناسی",
            "city": "تهران",
            "province": "تهران",
            "status": DeviceStatus.PRODUCTION,
        },
    )
    return created or device


def _align_to_interval(dt):
    minute = (dt.minute // 3) * 3
    return dt.replace(minute=minute, second=0, microsecond=0)


def seed_device_ospm(*, force: bool):
    existing = OSPM.objects.filter(device_id=DEVICE_ID).count()
    if existing >= OSPM_ROW_COUNT and not force:
        return 0

    if force and existing:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM device_ospm WHERE device_id = %s;",
                [DEVICE_ID],
            )
        LatestData.objects.filter(deviceinfo_id=DEVICE_ID).delete()

    end = _align_to_interval(timezone.localtime(timezone.now()))
    start = end - INTERVAL * (OSPM_ROW_COUNT - 1)
    random.seed(DEVICE_ID)
    suspicious_indices = set(random.sample(range(OSPM_ROW_COUNT), SUSPICIOUS_COUNT))

    rows = []
    for i in range(OSPM_ROW_COUNT):
        created_datetime = start + INTERVAL * i
        status = (
            DataStatus.SUSPICIOUS
            if i in suspicious_indices
            else DataStatus.PRODUCTION
        )
        rows.append(
            OSPM(
                created_datetime=created_datetime,
                device_id=DEVICE_ID,
                pm10=round(35.0 + (i % 17) * 1.3, 2),
                pm25=round(18.0 + (i % 13) * 0.9, 2),
                temperature=round(22.0 + (i % 9) * 0.4, 2),
                humidity=round(42.0 + (i % 11) * 0.7, 2),
                status=status,
            )
        )

    OSPM.objects.bulk_create(rows, batch_size=500)
    return len(rows)


def sync_latest_online():
    updated = 0
    for status in (DataStatus.PRODUCTION, DataStatus.SUSPICIOUS):
        reading = (
            OSPM.objects.filter(device_id=DEVICE_ID, status=status)
            .order_by("-created_datetime")
            .first()
        )
        if reading is None:
            continue
        LatestData.objects.update_or_create(
            deviceinfo_id=DEVICE_ID,
            status=status,
            granularity=Granularity.THREE_MINUTE,
            defaults={
                "created_datetime": reading.created_datetime,
                "data": {
                    "pm10": reading.pm10,
                    "pm25": reading.pm25,
                    "temperature": reading.temperature,
                    "humidity": reading.humidity,
                },
            },
        )
        updated += 1
    return updated


class Command(BaseCommand):
    help = (
        "Seed admin user, device 500, device_ospm sample data, latest rows, "
        "and refresh Timescale continuous aggregates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-ospm",
            action="store_true",
            help="Replace existing device_ospm rows for device 500.",
        )
        parser.add_argument(
            "--skip-cagg-refresh",
            action="store_true",
            help="Skip refresh_continuous_aggregate for hourly/daily views.",
        )

    def handle(self, *args, **options):
        force_ospm = options["force_ospm"]
        skip_cagg = options["skip_cagg_refresh"]

        if ensure_superuser():
            self.stdout.write(self.style.SUCCESS("Created superuser admin."))
        else:
            self.stdout.write("Superuser admin already exists; skipped.")

        ensure_device_info()
        self.stdout.write(
            self.style.SUCCESS(f"DeviceInfo device_id={DEVICE_ID} ready.")
        )

        inserted = seed_device_ospm(force=force_ospm)
        if inserted:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Inserted {inserted} device_ospm rows "
                    f"({SUSPICIOUS_COUNT} suspicious, "
                    f"{inserted - SUSPICIOUS_COUNT} production)."
                )
            )
        else:
            self.stdout.write(
                f"device_ospm already has >= {OSPM_ROW_COUNT} rows for "
                f"device {DEVICE_ID}; skipped (use --force-ospm to replace)."
            )

        latest_count = sync_latest_online()
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {latest_count} device_latest online (3-min) rows."
            )
        )

        if skip_cagg:
            self.stdout.write("Skipped continuous aggregate refresh.")
            return

        refresh_continuous_aggregates()
        self.stdout.write(
            self.style.SUCCESS(
                "Refreshed continuous aggregates: "
                + ", ".join(CAGG_VIEWS)
            )
        )
