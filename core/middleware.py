"""
BOS – CORS Middleware
=====================
Simple CORS middleware for development.
Allows the Next.js frontend (port 3000) to talk to the Django API (port 8000).
"""

from django.http import HttpResponse


class CorsMiddleware:
    """Handle CORS preflight and add headers to all responses."""

    ALLOWED_ORIGINS = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle OPTIONS preflight
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        origin = request.META.get("HTTP_ORIGIN", "")
        if origin in self.ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-API-KEY, X-BUSINESS-ID, X-BRANCH-ID"
            )
            response["Access-Control-Max-Age"] = "86400"

        return response
