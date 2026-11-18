"""Regression checks for the RESTX documentation and HTTP integration."""

from datetime import date, datetime, timezone
from decimal import Decimal
from itertools import product
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import UUID

from flask import Flask, jsonify

from wsgi import app
from service.common.api import OrdersApi


class TestRestx(TestCase):
    """Keep the documented API and the existing public URLs consistent."""

    def setUp(self):
        self.client = app.test_client()

    def test_documentation_keeps_admin_page(self):
        """It should serve Swagger UI separately from the existing admin page."""
        response = self.client.get("/apidocs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.content_type)
        self.assertIn(b"swagger-ui", response.data)
        response.close()

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h1>Orders</h1>", response.data)
        response.close()

    def test_admin_page_can_be_registered_after_api(self):
        """It should reserve the homepage for Flask regardless of registration order."""
        for doc in ("/apidocs", False):
            with self.subTest(doc=doc):
                isolated_app = Flask(__name__)
                api = OrdersApi(isolated_app, doc=doc)
                isolated_app.add_url_rule("/", "index", lambda: "Orders admin page")
                client = isolated_app.test_client()

                response = client.get("/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b"Orders admin page")
                with isolated_app.test_request_context():
                    self.assertEqual(api.base_path, "/")
                self.assertEqual(client.get("/swagger.json").get_json()["basePath"], "/")
                self.assertEqual(client.get("/apidocs").status_code, 200 if doc else 404)

    def test_documented_operations_keep_existing_paths(self):
        """It should document every order and item operation under the shared API prefix."""
        response = self.client.get("/api/swagger.json")
        self.assertEqual(response.status_code, 200)
        spec = response.get_json()
        self.assertEqual(spec["swagger"], "2.0")
        self.assertEqual(spec["basePath"], "/api")
        expected = {
            "/orders": {"get", "post"},
            "/orders/{order_id}": {"get", "put", "delete"},
            "/orders/{order_id}/cancel": {"put"},
            "/orders/{order_id}/items": {"get", "post"},
            "/orders/{order_id}/items/{item_id}": {"get", "put", "delete"},
        }
        self.assertEqual(set(spec["paths"]), set(expected))
        for path, methods in expected.items():
            with self.subTest(path=path):
                operations = spec["paths"][path]
                self.assertEqual(set(operations) - {"parameters"}, methods)
                for method in methods:
                    self.assertEqual(operations[method]["tags"], ["orders"])

    def test_documented_inputs_and_outputs(self):
        """It should document nested items, read-only values, filters and creation headers."""
        spec = self.client.get("/api/swagger.json").get_json()
        definitions = spec["definitions"]
        self.assertEqual(definitions["OrderInput"]["required"], ["customer_id"])
        self.assertEqual(definitions["ItemInput"]["required"], ["product_id", "quantity", "unit_price"])
        order_properties = definitions["Order"]["allOf"][1]["properties"]
        item_properties = definitions["Item"]["allOf"][1]["properties"]
        self.assertTrue(order_properties["id"]["readOnly"])
        self.assertTrue(item_properties["order_id"]["readOnly"])
        items = order_properties["items"]
        self.assertEqual(items["items"]["$ref"], "#/definitions/Item")
        orders = spec["paths"]["/orders"]
        query_names = {parameter["name"] for parameter in orders["get"]["parameters"]}
        self.assertEqual(query_names, {"customer_id", "status"})
        self.assertIn("Location", orders["post"]["responses"]["201"]["headers"])
        self.assertIn("409", spec["paths"]["/orders/{order_id}/cancel"]["put"]["responses"])

    def test_unsupported_resource_method_preserves_error_contract(self):
        """It should preserve JSON errors, request IDs and Allow on RESTX resources."""
        response = self.client.patch("/api/orders", headers={"X-Request-ID": "restx-method-test"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"], "Method not Allowed")
        self.assertEqual(set(response.get_json()), {"status", "error", "message"})
        self.assertEqual(response.headers["X-Request-ID"], "restx-method-test")
        self.assertEqual(set(response.headers["Allow"].split(", ")), {"GET", "POST", "HEAD", "OPTIONS"})

    def test_json_responses_match_flask_provider(self):
        """It should retain jsonify's exact bytes for objects, lists and creation responses."""
        payload = {"status": "NEW", "id": 123, "customer_id": 7, "items": [], "label": "café"}
        order = Mock(id=123)
        order.serialize.return_value = payload
        cases = (
            ("GET", "/api/orders", [payload], 200),
            ("GET", "/api/orders/123", payload, 200),
            ("POST", "/api/orders", payload, 201),
        )
        with patch("service.routes.Order") as order_model:
            order_model.return_value = order
            order_model.find.return_value = order
            order_model.all.return_value = [order]
            for debug, (method, path, body, code) in product((False, True), cases):
                with (
                    self.subTest(debug=debug, method=method, path=path),
                    patch.dict(app.config, {"DEBUG": debug}),
                ):
                    with app.app_context():
                        expected = jsonify(body)
                    response = self.client.open(
                        path, method=method, json={"customer_id": 7},
                        headers={"X-Request-ID": "restx-json-test"},
                    )
                    self.assertEqual(response.status_code, code)
                    self.assertEqual(response.data, expected.data)
                    self.assertEqual(response.content_type, expected.content_type)
                    self.assertEqual(response.headers["X-Request-ID"], "restx-json-test")
                    if code == 201:
                        self.assertEqual(response.headers["Location"], "http://localhost/api/orders/123")

    def test_json_responses_support_flask_types(self):
        """It should use Flask's Decimal, date, datetime and UUID encoders."""
        payload = {
            "subtotal": Decimal("12.50"),
            "created_at": datetime(2026, 11, 17, 12, tzinfo=timezone.utc),
            "date": date(2026, 11, 17),
            "reference": UUID("12345678-1234-5678-1234-567812345678"),
        }
        order = Mock()
        order.serialize.return_value = payload
        with app.app_context():
            expected = jsonify(payload)
        with patch("service.routes.Order.find", return_value=order):
            response = self.client.get("/api/orders/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected.data)
        self.assertEqual(response.content_type, expected.content_type)

    def test_delete_responses_match_flask(self):
        """It should retain empty Flask 204 responses for existing and absent records."""
        cases = (
            ("/api/orders/123", Mock(), None),
            ("/api/orders/123", None, None),
            ("/api/orders/123/items/456", None, Mock(order_id=123)),
            ("/api/orders/123/items/456", None, None),
            ("/api/orders/123/items/456", None, Mock(order_id=999)),
        )
        with app.app_context():
            expected = app.make_response(("", 204))
        for path, order, item in cases:
            with self.subTest(path=path, order=order, item=item):
                with (
                    patch("service.routes.Order.find", return_value=order),
                    patch("service.routes.Item.find", return_value=item),
                ):
                    response = self.client.delete(path, headers={"X-Request-ID": "restx-delete-test"})
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.data, b"")
                self.assertEqual(response.content_type, expected.content_type)
                self.assertNotIn("Content-Length", response.headers)
                self.assertEqual(response.headers["X-Request-ID"], "restx-delete-test")
