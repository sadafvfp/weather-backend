from rest_framework.exceptions import APIException
from rest_framework import status


class DataDropped(APIException):
    status_code = status.HTTP_202_ACCEPTED
    default_detail = "Data dropped because it arrived before the minimum period."
    default_code = "data_dropped"
