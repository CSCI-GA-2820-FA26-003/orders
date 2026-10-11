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

    def _assert_error(self, response, code: int, error: str, message: str):
        """Checks the response tuple returned by an error handler"""
        body, status_code = response
        self.assertEqual(status_code, code)
        data = body.get_json()
        self.assertEqual(data["status"], code)
        self.assertEqual(data["error"], error)
        self.assertEqual(data["message"], message)

    def test_data_validation_error(self):
        """It should return 400 for a DataValidationError"""
        response = error_handlers.request_validation_error(
            DataValidationError("bad data")
        )
        self._assert_error(
            response, status.HTTP_400_BAD_REQUEST, "Bad Request", "bad data"
        )

    def test_bad_request(self):
        """It should return 400 for a bad request"""
        response = error_handlers.bad_request("bad request")
        self._assert_error(
            response, status.HTTP_400_BAD_REQUEST, "Bad Request", "bad request"
        )

    def test_not_found(self):
        """It should return 404 for a URL that does not exist"""
        resp = self.client.get("/no-such-url")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"], "Not Found")

    def test_method_not_allowed(self):
        """It should return 405 for a method that is not supported"""
        resp = self.client.delete("/")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(data["error"], "Method not Allowed")

    def test_unsupported_media_type(self):
        """It should return 415 for an unsupported media type"""
        response = error_handlers.mediatype_not_supported("bad media type")
        self._assert_error(
            response,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported media type",
            "bad media type",
        )

    def test_internal_server_error(self):
        """It should return 500 for an internal server error"""
        response = error_handlers.internal_server_error("server error")
        self._assert_error(
            response,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            "server error",
        )
