"""Regression checks for the RESTX documentation and HTTP integration."""

from unittest import TestCase

from wsgi import app


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

    def test_documented_operations_keep_existing_paths(self):
        """It should document every order and item operation without an API prefix."""
        response = self.client.get("/swagger.json")
        self.assertEqual(response.status_code, 200)
        spec = response.get_json()
        self.assertEqual(spec["swagger"], "2.0")
        self.assertEqual(spec["basePath"], "/")
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
        spec = self.client.get("/swagger.json").get_json()
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
        response = self.client.patch("/orders", headers={"X-Request-ID": "restx-method-test"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"], "Method not Allowed")
        self.assertEqual(set(response.get_json()), {"status", "error", "message"})
        self.assertEqual(response.headers["X-Request-ID"], "restx-method-test")
        self.assertEqual(set(response.headers["Allow"].split(", ")), {"GET", "POST", "HEAD", "OPTIONS"})
