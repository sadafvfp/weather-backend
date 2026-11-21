import time
from rest_framework.test import APIClient


def test_hourly_timing():
    client = APIClient()
    # client.force_authenticate(user=user)  # if the endpoint needs auth

    url = "/kwz/history/air/online/لردگان-تهران-خوزستان/?end_date=2026-07-02+00%3A00%3A00&start_date=2026-06-01+23%3A50%3A00&page_size=14400"  # adjust path and params

    timings = []
    for _ in range(5):
        t0 = time.perf_counter()
        response = client.get(url)
        timings.append(time.perf_counter() - t0)
        assert response.status_code == 200

    print(f"rows: {len(response.json()['results'])}")
    print(f"runs: {[f'{t:.3f}' for t in timings]}")
    print(f"best: {min(timings):.3f}s")
