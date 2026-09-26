"""Custom error handlers.

The API returns JSON errors so the Next.js client can render its own styled
404/500 pages, rather than leaking Django's default HTML.
"""

from django.http import JsonResponse


def not_found(request, exception=None):
    return JsonResponse(
        {"detail": "منبع مورد نظر یافت نشد.", "code": "not_found"},
        status=404,
    )


def server_error(request):
    return JsonResponse(
        {"detail": "خطای داخلی سرور رخ داد.", "code": "server_error"},
        status=500,
    )


def protected_media(request):
    """Serve a private upload against a signed, short-lived token.

    Deliberately AllowAny: the token *is* the authorisation. Panels embed these
    URLs in <img src>, where no Authorization header is ever sent.
    """
    from apps.core.protected import serve_signed

    return serve_signed(request.GET.get("t", ""))
