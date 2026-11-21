# from datetime import datetime

# from django.utils.decorators import method_decorator
# from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import condition, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
# from django.views.generic import TemplateView


# def robots_last_modified(request):
#     return datetime(2023, 11, 18, 12, 40)


# @method_decorator(
#     cache_page(365 * 24 * 60 * 60, key_prefix="robots"), name="get"
# )  # 365 days
# @method_decorator(
#     cache_control(
#         public=True, max_age=3 * 24 * 60 * 60, must_revalidate=True
#     ),  # 3 days
#     name="get",
# )
# @method_decorator(condition(last_modified_func=robots_last_modified), name="get")
# class RobotsBlockView(TemplateView):
#     template_name = "robots-block.txt"
#     content_type = "text/plain"


@require_GET
@ensure_csrf_cookie
def csrf(request):
    from django.middleware.csrf import get_token

    return JsonResponse({"detail": "CSRF cookie set", "csrfToken": get_token(request)})
