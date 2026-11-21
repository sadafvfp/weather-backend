import requests
from unittest.mock import Mock
import pytest

from backend.apps.device.services import MunicipalityForwardingService
from backend.apps.device.exceptions import MunicipalityAPIError

payload = {
    "device_id": 136,
    "pm10": 30,
    "pm25": 30,
    "so2": 30,
    "no2": 30,
    "o3": 30,
    "co": 30,
    "temperature": 30,
    "humidity": 30,
}


def test_municipality_success(mocker, settings):
    settings.MUNICIPALITY_SHRZ_AUTH_TOKEN = "secret"
    settings.MUNICIPALITY_API_URL = "https://municipality.test/api"
    settings.MUNICIPALITY_API_TIMEOUT = 10

    response = Mock()
    response.raise_for_status.return_value = None

    post = mocker.patch(
        "backend.apps.device.services.requests.post",
        return_value=response,
    )

    MunicipalityForwardingService.forward(
        "SAPA",
        payload,
    )

    post.assert_called_once()

    kwargs = post.call_args.kwargs

    assert kwargs["headers"] == {"Authorization": "Api-Key secret"}

    assert kwargs["timeout"] == 10


def test_municipality_400_is_not_retryable(mocker, settings):
    response = Mock()

    http_error = requests.exceptions.HTTPError(response=Mock(status_code=400))

    response.raise_for_status.side_effect = http_error

    mocker.patch(
        "backend.apps.device.services.requests.post",
        return_value=response,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        MunicipalityForwardingService.forward("SAPA", payload)


def test_municipality_500_becomes_retryable_error(mocker):
    response = Mock()

    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=500)
    )

    mocker.patch(
        "backend.apps.device.services.requests.post",
        return_value=response,
    )

    with pytest.raises(MunicipalityAPIError) as exc:
        MunicipalityForwardingService.forward("SAPA", payload)

    assert exc.value.status_code == 500


def test_forward_task_retries_on_municipality_error(mocker):
    from backend.apps.device.tasks import forward_reading_to_municipality

    mocker.patch(
        "backend.apps.device.tasks.MunicipalityForwardingService.forward",
        side_effect=MunicipalityAPIError("timeout"),
    )

    retry = mocker.patch.object(
        forward_reading_to_municipality,
        "retry",
        side_effect=RuntimeError("retry-called"),
    )

    with pytest.raises(RuntimeError, match="retry-called"):
        forward_reading_to_municipality.run("SAPA", payload)

    retry.assert_called_once()
