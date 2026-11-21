from datetime import timedelta


from backend.settings.base import get_env_var
from .models import DataStatus

DEFAULT_SENSOR_THRESHOLD = {
    "so2": (0, 1100),
    "no2": (0, 1100),
    "co": (0, 13000),
    "o3": (0, 1100),
    "pm10": (0, 500),
    "pm25": (0, 500),
    "temperature": (-45, 95),
    "humidity": (0, 100),
    "flow": (0, 1000),
}


DEFAULT_MIN_GAP_MAP = {
    DataStatus.TEST: timedelta(seconds=int(get_env_var("DEFAULT_MIN_GAP_TEST", 30))),
    DataStatus.PRODUCTION: timedelta(
        seconds=int(get_env_var("DEFAULT_MIN_GAP_PRODUCTION", 120))
    ),
    DataStatus.SUSPICIOUS: timedelta(
        seconds=int(get_env_var("DEFAULT_MIN_GAP_SUSPICIOUS", 60))
    ),
}


SOUND_THRESHOLD = {
    "leq": (20, 145),
    "spl": (20, 145),
    "spl_min": (20, 145),
    "spl_max": (20, 145),
    "temperature": (-45, 95),
    "humidity": (0, 100),
    "pressure": (0, 120),
}
