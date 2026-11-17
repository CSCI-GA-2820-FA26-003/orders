"""Flask-RESTX integration with the service's existing error contract."""

from flask_restx import Api


class OrdersApi(Api):
    """Document resources while keeping Flask's JSON error handlers in charge."""

    def error_router(self, original_handler, e):
        """Preserve error bodies, HTTP headers and safe server-error messages."""
        return original_handler(e)
