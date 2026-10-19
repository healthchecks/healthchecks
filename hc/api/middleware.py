from django.db import connection
from django.http import HttpRequest, HttpResponse

from hc.lib.typealias import MiddlewareFunc


class HealthMiddleware:
    def __init__(self, get_response: MiddlewareFunc) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == "/health":
            with connection.cursor() as c:
                c.execute("SELECT 1")
                c.fetchone()

            return HttpResponse("OK")

        return self.get_response(request)
