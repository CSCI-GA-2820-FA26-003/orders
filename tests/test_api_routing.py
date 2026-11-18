"""API namespace and routing-error regression tests."""
from unittest import TestCase
from unittest.mock import patch

from wsgi import app
from service.models import db


class TestApiRouting(TestCase):
    """Check API URLs and errors independently of business operations."""

    def setUp(self):
        """Create a request client."""
        self.client = app.test_client()

    def assert_json_error(self, response, expected_status):
        """Check the existing error envelope."""
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.mimetype, "application/json")
        body = response.get_json()
        self.assertEqual(set(body), {"status", "error", "message"})
        self.assertEqual(body["status"], expected_status)
        self.assertTrue(body["error"])
        self.assertTrue(body["message"])

    def test_missing_order_is_json(self):
        """It should return the existing JSON 404 at the new lookup URL."""
        self.assert_json_error(self.client.get("/api/orders/2147483647"), 404)

    def test_unsupported_method_preserves_allow(self):
        """It should return JSON 405 and preserve the HTTP Allow header."""
        response = self.client.patch("/api/orders", headers={"X-Request-ID": "api-routing-test"})
        self.assert_json_error(response, 405)
        self.assertTrue({"GET", "POST"}.issubset(set(response.headers["Allow"].replace(" ", "").split(","))))
        self.assertEqual(response.headers["X-Request-ID"], "api-routing-test")

    def test_unknown_api_path_is_json(self):
        """It should return JSON for an unknown API URL without accessing the database."""
        with patch.object(db.session, "execute", side_effect=AssertionError("Unexpected database query")):
            self.assert_json_error(self.client.get("/api/missing"), 404)

    def test_old_collection_url_is_not_an_api_alias(self):
        """It should return JSON 404 for the former collection URL."""
        self.assert_json_error(self.client.get("/orders"), 404)

    def test_homepage_and_health_keep_their_urls(self):
        """It should retain the root URL and database-independent health endpoint."""
        self.assertEqual(self.client.get("/").status_code, 200)
        with patch.object(db.session, "execute", side_effect=AssertionError("Unexpected database query")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "OK"})
