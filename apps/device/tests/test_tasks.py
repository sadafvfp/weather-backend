# def test_forward_task_retries_on_municipality_error(mocker):
#     from device.tasks import forward_reading_to_municipality

#     mocker.patch(
#         "device.tasks.MunicipalityForwardingService.forward",
#         side_effect=MunicipalityAPIError("timeout"),
#     )

#     retry = mocker.patch.object(
#         forward_reading_to_municipality,
#         "retry",
#         side_effect=RuntimeError("retry-called"),
#     )

#     with pytest.raises(RuntimeError, match="retry-called"):
#         forward_reading_to_municipality.run(
#             "SAPA",
#             {
#                 "device_id": 136,
#                 "pm10": 30,
#                 "created_datetime": "2026-09-17T10:00:00+03:30",
#             },
#         )

#     retry.assert_called_once()
