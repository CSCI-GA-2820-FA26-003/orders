######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Error Handlers Test Suite
"""

import logging
from unittest import TestCase
from unittest.mock import patch
from datetime import datetime, timezone
from werkzeug.exceptions import Unauthorized, Forbidden, TooManyRequests, ServiceUnavailable, BadGateway
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.http import http_date
from wsgi import app
from service.common import status, error_handlers
from service.models import DataValidationError


######################################################################
#  T E S T   C A S E S
######################################################################
class TestErrorHandlers(TestCase):
    """Error Handler Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        """This runs after each test"""
        self.ctx.pop()

    def _assert_error(
        self,
        response,
        code: int,
        error_code: str,
        message: str,
        details=None,
    ):
        """Checks the response tuple returned by an error handler"""
        body, status_code = response
        self.assertEqual(status_code, code)
        self.assertIn("application/json", body.mimetype)
        data = body.get_json()
        self.assertEqual(data["status"], code)
        self.assertEqual(data["error"]["code"], error_code)
        self.assertEqual(data["error"]["message"], message)
        self.assertIn("request_id", data["error"])
        self.assertEqual(data["error"]["request_id"], response[0].headers["X-Request-ID"])
        if details is None:
            self.assertNotIn("details", data["error"])
        else:
            self.assertEqual(data["error"]["details"], details)

    def test_data_validation_error(self):
        """It should return 400 for a DataValidationError"""
        response = error_handlers.request_validation_error(
            DataValidationError("bad data")
        )
        self._assert_error(
            response,
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "bad data",
            details=[{"field": "request", "reason": "bad data"}],
        )

    def test_bad_request(self):
        """It should return 400 for a bad request"""
        response = error_handlers.bad_request("bad request")
        self._assert_error(
            response,
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "bad request",
            details=[{"field": "request", "reason": "bad request"}],
        )

    def test_not_found(self):
        """It should return 404 for a URL that does not exist"""
        resp = self.client.get("/no-such-url")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("application/json", resp.content_type)
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertIn("request_id", data["error"])

    def test_method_not_allowed(self):
        """It should return 405 for a method that is not supported"""
        resp = self.client.delete("/")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(data["error"]["code"], "method_not_allowed")
        self.assertEqual(set(resp.headers["Allow"].split(", ")), {"GET", "HEAD", "OPTIONS"})

    def test_unsupported_media_type(self):
        """It should return 415 for an unsupported media type"""
        response = error_handlers.mediatype_not_supported("bad media type")
        self._assert_error(
            response,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "unsupported_media",
            "bad media type",
        )

    def test_internal_server_error(self):
        """It should return 500 for an internal server error"""
        response = error_handlers.internal_server_error(RuntimeError("internal details"))
        self._assert_error(
            response,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
        self.assertNotIn("internal details", response[0].get_data(as_text=True))

    def test_service_unavailable(self):
        """It should return 503 for an unavailable service"""
        response = error_handlers.service_unavailable(RuntimeError("degraded service"))
        self._assert_error(
            response,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "unavailable",
            "The service is temporarily unavailable.",
        )

    def test_http_errors_preserve_status_and_headers(self):
        """It should preserve unhandled HTTP statuses, authentication challenges, and retry headers."""
        cases = [
            (Unauthorized(www_authenticate=WWWAuthenticate("basic", {"realm": "orders"})),
             "unauthorized", "WWW-Authenticate", 'Basic realm=orders'),
            (Forbidden(), "forbidden", None, None),
            (TooManyRequests(retry_after=30), "too_many_requests", "Retry-After", "30"),
        ]
        for error, error_code, header, value in cases:
            with self.subTest(status=error.code):
                with patch("service.routes.Order.find", side_effect=error):
                    resp = self.client.delete("/orders/123", headers={"X-Request-ID": "http-error-test"})
                self._assert_error((resp, resp.status_code), error.code, error_code, str(error))
                self.assertEqual(resp.headers["X-Request-ID"], "http-error-test")
                if header:
                    self.assertEqual(resp.headers[header], value)

    def test_service_unavailable_preserves_retry_after(self):
        """It should preserve both Retry-After formats and hide internal 503 details."""
        retry_date = datetime(2030, 1, 1, tzinfo=timezone.utc)
        for retry_after, expected in ((30, "30"), (retry_date, http_date(retry_date))):
            with self.subTest(retry_after=retry_after):
                error = ServiceUnavailable(description="private database failure", retry_after=retry_after)
                with patch("service.routes.Order.find", side_effect=error):
                    resp = self.client.delete("/orders/123")
                self._assert_error(
                    (resp, resp.status_code), 503, "unavailable", "The service is temporarily unavailable."
                )
                self.assertEqual(resp.headers["Retry-After"], expected)
                self.assertNotIn("private database failure", resp.get_data(as_text=True))

    def test_unexpected_exception_returns_safe_500(self):
        """It should return a safe JSON 500 for unexpected server exceptions."""
        with patch("service.routes.Order.find", side_effect=RuntimeError("private database failure")):
            resp = self.client.delete("/orders/123")
        self._assert_error((resp, resp.status_code), 500, "internal_error", "An unexpected error occurred.")
        self.assertNotIn("private database failure", resp.get_data(as_text=True))

    def test_unhandled_server_http_error_is_safe(self):
        """It should preserve other server HTTP statuses without exposing internal details."""
        with patch("service.routes.Order.find", side_effect=BadGateway(description="private upstream details")):
            resp = self.client.delete("/orders/123")
        self._assert_error((resp, resp.status_code), 502, "internal_error", "An unexpected error occurred.")
        self.assertNotIn("private upstream details", resp.get_data(as_text=True))
