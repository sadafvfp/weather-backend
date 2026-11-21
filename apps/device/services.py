import json
import logging
from datetime import timedelta
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, IntegrityError, transaction
from django.db.models import Min, Max
from django.conf import settings
from django.apps import apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError


from ..device.models import (
    DeviceStatus,
    DataStatus,
    LatestData,
    Granularity,
    DeviceInfo,
    OSPM,
)
from .exceptions import DataDropped
from .constants import DEFAULT_SENSOR_THRESHOLD, DEFAULT_MIN_GAP_MAP
from .utils import match_time_format, check_threshold, normalize_three_minute_datetime
from .sensor_codes import has_sensor_error, normalize_error_code

logger = logging.getLogger(__name__)

BATCH_ACK_TTL_SECONDS = 15 * 60  # 15 minutes for duplicate retry fast-path
CAGG_WINDOW_TTL_SECONDS = 2 * 60 * 60  # 2 hours for rolling CAGG window state
CAGG_MIN_AGE = timedelta(
    hours=1
)  # Only refresh CAGG if oldest healthy record >= 1h old
CAGG_FALLBACK_COUNTDOWN = 5 * 60  # 5 minutes fallback if last batch never arrives


class InfoService:
    @staticmethod
    def get_device(device_id):
        try:
            return DeviceInfo.objects.get(device_id=device_id)
        except DeviceInfo.DoesNotExist:
            return None

    @staticmethod
    def get_device_by_slug(slug):
        try:
            return DeviceInfo.objects.get(slug=slug)
        except DeviceInfo.DoesNotExist:
            return None


class LatestDataService:
    @staticmethod
    @transaction.atomic
    def try_accept_and_store(device_info, status, payload, min_gap):
        """
        Returns (accepted, prev_created_datetime, prev_data).
        prev_* are the reading this one is replacing, or (None, None) if
        there wasn't one (device's first reading) or it was rejected.
        """
        payload = payload.copy()
        new_datetime = payload.pop("created_datetime")
        cutoff = new_datetime - min_gap
        lookup = {
            "deviceinfo_id": device_info.device_id,
            "status": status,
            "granularity": Granularity.THREE_MINUTE,
        }

        try:
            row, created = LatestData.objects.select_for_update().get_or_create(
                **lookup,
                defaults={"created_datetime": new_datetime, "data": payload},
            )
        except IntegrityError:
            # Two concurrent first-readings for the same device both missed
            # the get() (select_for_update can't lock a row that doesn't
            # exist yet) and both tried to insert. The loser lands here —
            # fetch the row the winner created and fall through to the
            # normal update path.
            row = LatestData.objects.select_for_update().get(**lookup)
            created = False
        if created:
            return True

        if row.created_datetime is not None and row.created_datetime > cutoff:
            return False

        row.created_datetime, row.data = new_datetime, payload
        row.save(update_fields=["created_datetime", "data"])
        return True

    @staticmethod
    def upsert_latest_pair_if_newer(
        device_id, latest_h_record=None, latest_s_record=None
    ):
        """
        Updates LatestData for both Healthy (PRODUCTION) and Suspicious (SUSPICIOUS)
        in a SINGLE SQL query using ON CONFLICT DO UPDATE ... WHERE EXCLUDED.created_datetime > device_latest.created_datetime.
        Older historical batches will never overwrite newer LatestData rows.
        """
        candidates = []
        if latest_h_record is not None:
            candidates.append((DataStatus.PRODUCTION, latest_h_record))
        if latest_s_record is not None:
            candidates.append((DataStatus.SUSPICIOUS, latest_s_record))

        if not candidates:
            return

        values_sql = []
        params = []
        for data_status, rec in candidates:
            dt = rec["created_datetime"]
            payload_data = {
                "device_id": device_id,
                "pm10": rec["pm10"],
                "pm25": rec["pm25"],
                "temperature": rec["temperature"],
                "humidity": rec["humidity"],
                "flow": rec.get("flow"),
                "error_code": rec.get("error_code"),
                "status": int(data_status),
            }
            values_sql.append("(%s, %s, %s, %s, %s::jsonb)")
            params.extend(
                [
                    device_id,
                    int(data_status),
                    int(Granularity.THREE_MINUTE),
                    dt,
                    json.dumps(payload_data, cls=DjangoJSONEncoder),
                ]
            )

        sql = f"""
            INSERT INTO device_latest (deviceinfo_id, status, granularity, created_datetime, data)
            VALUES {", ".join(values_sql)}
            ON CONFLICT (deviceinfo_id, status, granularity)
            DO UPDATE SET
                created_datetime = EXCLUDED.created_datetime,
                data = EXCLUDED.data
            WHERE device_latest.created_datetime IS NULL
               OR EXCLUDED.created_datetime > device_latest.created_datetime;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)


class IngestionService:

    @staticmethod
    def prepare_reading(
        device_info, validated_data, min_gap_map=None, sensor_threshold=None
    ):
        validated_data["created_datetime"] = timezone.localtime(timezone.now())
        validated_data["device_id"] = device_info.device_id
        if "error_code" in validated_data:
            validated_data["error_code"] = normalize_error_code(
                validated_data.get("error_code")
            )
        min_gap_map = {**DEFAULT_MIN_GAP_MAP, **(min_gap_map or {})}

        if device_info.status == DeviceStatus.TEST:
            data_status = DataStatus.TEST
            return IngestionService._handle_bucket(
                device_info,
                validated_data,
                data_status,
                min_gap_map[data_status],
            )

        if device_info.status == DeviceStatus.PRODUCTION:
            thresholds = {**DEFAULT_SENSOR_THRESHOLD, **(sensor_threshold or {})}
            data_status = DataStatus.PRODUCTION
            skip_threshold = {"error_code", "device_id", "created_datetime", "status"}
            for k, v in validated_data.items():
                if k in skip_threshold:
                    continue
                threshold = thresholds.get(k)
                if threshold and v is not None and not check_threshold(v, threshold):
                    data_status = DataStatus.SUSPICIOUS
                    break
            if has_sensor_error(validated_data.get("error_code")):
                data_status = DataStatus.SUSPICIOUS

            result = IngestionService._handle_bucket(
                device_info,
                validated_data,
                data_status,
                min_gap_map[data_status],
            )

            return result

        raise ValidationError(f"Unhandled device status: {device_info.status}")

    @staticmethod
    def _handle_bucket(device_info, validated_data, data_status, min_gap):
        accepted = LatestDataService.try_accept_and_store(
            device_info, data_status, validated_data, min_gap
        )
        if not accepted:
            raise DataDropped()
        validated_data["status"] = data_status
        return validated_data


class HistoryDataService:
    @staticmethod
    def store_reading(validated_data):
        OSPM.objects.bulk_create(
            [OSPM(**validated_data)],
            ignore_conflicts=True,
        )

    @staticmethod
    def _batch_cache_key(device_id, total_batch, batch_id, data_h, data_s):
        first_h = data_h[0]["created_datetime"].isoformat() if data_h else "none"
        last_h = data_h[-1]["created_datetime"].isoformat() if data_h else "none"
        first_s = data_s[0]["created_datetime"].isoformat() if data_s else "none"
        last_s = data_s[-1]["created_datetime"].isoformat() if data_s else "none"
        return (
            f"ospm_batch:{device_id}:{total_batch}:{batch_id}:"
            f"h({first_h}..{last_h}):s({first_s}..{last_s})"
        )

    @staticmethod
    def _cagg_window_key(device_id):
        return f"ospm_cagg_win:{device_id}"

    @classmethod
    def process_batch(cls, device_info, validated_payload):
        device_id = device_info.device_id
        total_batch = validated_payload["total_batch"]
        batch_id = validated_payload["batch_id"]
        data_h = validated_payload.get("data_h") or []
        data_s = validated_payload.get("data_s") or []

        batch_key = cls._batch_cache_key(
            device_id, total_batch, batch_id, data_h, data_s
        )
        # 1. Fast-path check in Redis if this exact batch was already committed
        try:
            if cache.get(batch_key):
                return {
                    "status": "ok",
                    "device_id": device_id,
                    "batch_id": batch_id,
                    "total_batch": total_batch,
                    "duplicate_batch": True,
                    "received_h": len(data_h),
                    "received_s": len(data_s),
                }
        except Exception:
            logger.warning(
                "Redis unavailable during batch check for device %s", device_id
            )

        # 2. Build combined OSPM model instances for a single bulk INSERT ... ON CONFLICT DO NOTHING
        ospm_objects = []
        for item in data_h:
            ospm_objects.append(
                OSPM(
                    device_id=device_id,
                    created_datetime=item["created_datetime"],
                    pm10=item["pm10"],
                    pm25=item["pm25"],
                    temperature=item["temperature"],
                    humidity=item["humidity"],
                    flow=item.get("flow"),
                    error_code=item.get("error_code"),
                    status=DataStatus.PRODUCTION,
                )
            )
        for item in data_s:
            ospm_objects.append(
                OSPM(
                    device_id=device_id,
                    created_datetime=item["created_datetime"],
                    pm10=item["pm10"],
                    pm25=item["pm25"],
                    temperature=item["temperature"],
                    humidity=item["humidity"],
                    flow=item.get("flow"),
                    error_code=item.get("error_code"),
                    status=DataStatus.SUSPICIOUS,
                )
            )

        latest_h = data_h[-1] if data_h else None
        latest_s = data_s[-1] if data_s else None

        # 3. Single atomic transaction for both device_ospm and device_latest
        with transaction.atomic():
            OSPM.objects.bulk_create(ospm_objects, ignore_conflicts=True)
            LatestDataService.upsert_latest_pair_if_newer(
                device_id=device_id,
                latest_h_record=latest_h,
                latest_s_record=latest_s,
            )
            transaction.on_commit(
                lambda: cls._post_commit_hooks(
                    device_id=device_id,
                    batch_key=batch_key,
                    batch_id=batch_id,
                    total_batch=total_batch,
                    data_h=data_h,
                )
            )

        return {
            "status": "ok",
            "device_id": device_id,
            "batch_id": batch_id,
            "total_batch": total_batch,
            "duplicate_batch": False,
            "received_h": len(data_h),
            "received_s": len(data_s),
        }

    @classmethod
    def _post_commit_hooks(cls, device_id, batch_key, batch_id, total_batch, data_h):
        """
        Runs strictly AFTER PostgreSQL commits the transaction:
        1. Marks batch_key in Redis so retries short-circuit safely.
        2. Tracks rolling [min_ts, max_ts] for healthy data (data_h) and triggers
           CAGG refresh on the last batch (or schedules a 5-min fallback timer
           if the last batch never arrives).
        """
        from .tasks import (
            refresh_ospm_continuous_aggregates,
            flush_pending_ospm_cagg_refresh,
        )

        try:
            cache.set(batch_key, "1", timeout=BATCH_ACK_TTL_SECONDS)
        except Exception:
            logger.warning("Failed to set batch_key in Redis for device %s", device_id)

        win_key = cls._cagg_window_key(device_id)
        now = timezone.localtime(timezone.now())

        try:
            state = cache.get(win_key) or {}
        except Exception:
            state = {}

        # Update rolling [min_ts, max_ts] if this batch had healthy data
        if data_h:
            batch_min_dt = data_h[0]["created_datetime"]
            batch_max_dt = data_h[-1]["created_datetime"]

            existing_min = (
                parse_datetime(state["min_ts"]) if state.get("min_ts") else None
            )
            existing_max = (
                parse_datetime(state["max_ts"]) if state.get("max_ts") else None
            )

            new_min = min(existing_min, batch_min_dt) if existing_min else batch_min_dt
            new_max = max(existing_max, batch_max_dt) if existing_max else batch_max_dt

            version = int(state.get("version", 0)) + 1
            state = {
                "min_ts": new_min.isoformat(),
                "max_ts": new_max.isoformat(),
                "version": version,
            }
            try:
                cache.set(win_key, state, timeout=CAGG_WINDOW_TTL_SECONDS)
            except Exception:
                logger.warning(
                    "Failed to update CAGG window in Redis for device %s", device_id
                )

        # If this is the final batch, flush and trigger CAGG refresh if oldest data >= 1 hour old
        if batch_id == total_batch:
            if state.get("min_ts") and state.get("max_ts"):
                min_dt = parse_datetime(state["min_ts"])
                try:
                    cache.delete(win_key)
                except Exception:
                    pass
                if min_dt is not None and (now - min_dt) >= CAGG_MIN_AGE:
                    refresh_ospm_continuous_aggregates.delay(
                        state["min_ts"], state["max_ts"]
                    )
        else:
            # Fallback in case the device disconnects and batch_id == total_batch never arrives
            if state.get("min_ts") and state.get("max_ts"):
                min_dt = parse_datetime(state["min_ts"])
                if min_dt is not None and (now - min_dt) >= CAGG_MIN_AGE:
                    flush_pending_ospm_cagg_refresh.apply_async(
                        args=[device_id, state["version"]],
                        countdown=CAGG_FALLBACK_COUNTDOWN,
                    )


class OSPMThreeMinuteDeletionService:
    THRESHOLD_FIELDS = ("created_datetime", "start_date", "end_date", "datetimes")

    @staticmethod
    def _normalize_bound(dt):
        return normalize_three_minute_datetime(dt)

    @classmethod
    def delete_for_device(cls, device_id, criteria, statuses):
        created_datetime = criteria.get("created_datetime")
        start_date = criteria.get("start_date")
        end_date = criteria.get("end_date")
        datetimes = criteria.get("datetimes") or []

        qs = OSPM.objects.filter(device_id=device_id, status__in=statuses)
        refresh_start = refresh_end = None

        if created_datetime is not None:
            bucket = cls._normalize_bound(created_datetime)
            qs = qs.filter(created_datetime=bucket)
            refresh_start = refresh_end = bucket
        elif datetimes:
            buckets = sorted({cls._normalize_bound(dt) for dt in datetimes})
            qs = qs.filter(created_datetime__in=buckets)
            refresh_start, refresh_end = buckets[0], buckets[-1]
        elif start_date is not None and end_date is not None:
            start = cls._normalize_bound(start_date)
            end = cls._normalize_bound(end_date)
            if end < start:
                raise ValidationError(
                    {"detail": "end_date must be greater than or equal to start_date."}
                )
            qs = qs.filter(created_datetime__gte=start, created_datetime__lte=end)
            refresh_start, refresh_end = start, end
        else:
            raise ValidationError(
                {
                    "detail": (
                        "Provide created_datetime, start_date/end_date, or datetimes."
                    )
                }
            )

        refresh_cagg = qs.filter(status=DataStatus.PRODUCTION).exists()
        deleted_count, _ = qs.delete()
        if not refresh_cagg:
            refresh_start = refresh_end = None
        return deleted_count, refresh_start, refresh_end

    @classmethod
    def delete_all_for_device(cls, device_id):
        qs = OSPM.objects.filter(device_id=device_id)
        prod_qs = qs.filter(status=DataStatus.PRODUCTION)
        bounds = prod_qs.aggregate(
            min_dt=Min("created_datetime"),
            max_dt=Max("created_datetime"),
        )
        refresh_start = bounds["min_dt"]
        refresh_end = bounds["max_dt"]
        if refresh_start is None or refresh_end is None:
            deleted_count, _ = qs.delete()
            return deleted_count, None, None
        deleted_count, _ = qs.delete()
        return deleted_count, refresh_start, refresh_end
