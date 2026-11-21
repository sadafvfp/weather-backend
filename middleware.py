from django.http import JsonResponse


class DisablePatchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "PATCH":
            return JsonResponse(
                {"detail": 'Method "PATCH" not allowed.'},
                status=405,
                headers={"Allow": "GET, POST, PUT, DELETE, HEAD, OPTIONS"},
            )
        return self.get_response(request)
