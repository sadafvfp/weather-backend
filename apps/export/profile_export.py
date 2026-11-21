# profile_export.py  (put it next to manage.py)
import os
import django
from django.conf import settings

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "backend.settings.api"
)  # adjust to your settings module
django.setup()
import logging

logging.getLogger("django.db.backends").setLevel(logging.WARNING)
settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def main():
    client = APIClient()
    user = User.objects.filter(is_superuser=True).first()  # or any user with access
    client.force_authenticate(user=user)
    query_params = {
        "start_date": "2026-06-20 23:50:00",
        "end_date": "2026-07-02 00:00:00",
    }
    resp = client.get(
        "http://127.0.0.1:8002/kwz/excel/air/online/%D9%84%D8%B1%D8%AF%DA%AF%D8%A7%D9%86-%D8%AA%D9%87%D8%B1%D8%A7%D9%86-%D8%AE%D9%88%D8%B2%D8%B3%D8%AA%D8%A7%D9%86/",  # your real URL
        {
            "format": "xlsx",
            "start_date": "2026-06-20 23:50:00",
            "end_date": "2026-07-02 00:00:00",
        },  # your real query params
    )
    print(resp.status_code)
    print(resp.content[:2000])
    print(getattr(resp, "data", None))
    assert resp.status_code == 200, (resp.status_code, resp.content[:300])
    print(resp.status_code, len(resp.content) / 1e6, "MB response")


if __name__ == "__main__":
    main()
