#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.utils.translation import gettext_lazy as _

DEFAULT_ERROR_MESSAGE = _(
    "The request could not be completed. Please try again or return to the home page."
)

ERROR_DATA = {
    # 4xx Client Error
    400: {
        "title": _("Bad request"),
        "eyebrow": _("Request issue"),
        "message": _("The request was malformed or contained invalid data."),
    },
    401: {
        "title": _("Authentication required"),
        "eyebrow": _("Sign in needed"),
        "message": _("Please sign in before opening this page."),
    },
    402: {"title": _("Payment required")},
    403: {
        "title": _("Access denied"),
        "eyebrow": _("Permission needed"),
        "message": _("You do not have permission to view this resource."),
    },
    404: {
        "title": _("Page not found"),
        "eyebrow": _("Missing page"),
        "message": _("The page may have moved, expired, or never existed."),
    },
    405: {
        "title": _("Method not allowed"),
        "message": _("This endpoint does not support the request method you used."),
    },
    406: {"title": _("Not acceptable")},
    407: {"title": _("Proxy authentication required")},
    408: {
        "title": _("Request timeout"),
        "message": _("The server waited too long for the request to finish."),
    },
    409: {"title": _("Conflict")},
    410: {"title": _("Gone")},
    411: {"title": _("Length required")},
    412: {"title": _("Precondition failed")},
    413: {
        "title": _("Payload too large"),
        "message": _("The submitted data is larger than this endpoint allows."),
    },
    414: {"title": _("URI too long")},
    415: {"title": _("Unsupported media type")},
    416: {"title": _("Requested range not satisfiable")},
    417: {"title": _("Expectation failed")},
    418: {"title": _("I'm a teapot")},
    421: {"title": _("Misdirected request")},
    422: {
        "title": _("Unprocessable entity"),
        "message": _("The server understood the request but could not process it."),
    },
    423: {"title": _("Locked")},
    424: {"title": _("Failed dependency")},
    426: {"title": _("Upgrade required")},
    428: {"title": _("Precondition required")},
    429: {
        "title": _("Too many requests"),
        "eyebrow": _("Rate limit"),
        "message": _("Please wait a moment before trying again."),
    },
    431: {"title": _("Request header fields too large")},
    444: {"title": _("Connection closed without response")},
    451: {"title": _("Unavailable for legal reasons")},
    499: {"title": _("Client closed request")},

    # 5xx Server Error
    500: {
        "title": _("Something went wrong"),
        "eyebrow": _("Server error"),
        "message": _("The server hit an unexpected problem. The team has been notified."),
    },
    501: {
        "title": _("Not implemented"),
        "message": _("This functionality is not available on the server yet."),
    },
    502: {
        "title": _("Bad gateway"),
        "eyebrow": _("Upstream error"),
        "message": _("A service we depend on did not respond correctly."),
    },
    503: {
        "title": _("Service unavailable"),
        "eyebrow": _("Temporarily unavailable"),
        "message": _("The service is temporarily unavailable. Please try again later."),
    },
    504: {
        "title": _("Gateway timeout"),
        "message": _("A service we depend on took too long to respond."),
    },
    505: {"title": _("HTTP version not supported")},
    506: {"title": _("Variant also negotiates")},
    507: {"title": _("Insufficient storage")},
    508: {"title": _("Loop detected")},
    510: {"title": _("Not extended")},
    511: {
        "title": _("Network authentication required"),
        "message": _("Please authenticate with the network before trying again."),
    },
    599: {
        "title": _("Network connect timeout"),
        "message": _("The network connection timed out before the server could respond."),
    },
}
