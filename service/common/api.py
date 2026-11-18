"""Flask-RESTX integration with the service's existing error contract."""

from flask_restx import Api


class OrdersApi(Api):
    """Document resources while keeping Flask's JSON error handlers in charge."""

    def _register_doc(self, app_or_blueprint):
        """Keep Swagger's base URL buildable without claiming Flask's homepage."""
        if self._add_specs and self._doc:
            app_or_blueprint.add_url_rule(self._doc, "doc", self.render_doc)
        # RESTX uses this endpoint for base_path/base_url; it must not match requests.
        app_or_blueprint.add_url_rule(self.prefix or "/", "root", build_only=True)

    def error_router(self, original_handler, e):
        """Preserve error bodies, HTTP headers and safe server-error messages."""
        return original_handler(e)
