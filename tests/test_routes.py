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
Orders API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from decimal import Decimal
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Order, Item
from tests.factories import OrderFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestOrderService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Item).delete()  # clean up the last tests
        db.session.query(Order).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

    def test_index_service_information(self):
        """It should describe the service and its version as JSON"""
        data = self.client.get("/").get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["name"], "Orders Service")
        self.assertEqual(data["version"], "1.0.0")

    def test_index_orders_endpoint(self):
        """It should advertise the existing Orders collection endpoint"""
        data = self.client.get("/").get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["endpoints"]["orders"], "/orders")
        resp = self.client.get(data["endpoints"]["orders"])
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.get_json(), list)

    ######################################################################
    #  C R E A T E   A N   O R D E R
    ######################################################################

    def test_create_an_order(self):
        """It should Create an Order"""
        payload = {"customer_id": 123}

        resp = self.client.post("/orders", json=payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["customer_id"], 123)
        self.assertEqual(data["status"], "NEW")
        self.assertEqual(data["items"], [])
        self.assertEqual(
            resp.headers["Location"], f"http://localhost/orders/{data['id']}"
        )
        self.assertIsNotNone(Order.find(data["id"]))

    def test_create_order_without_customer_id(self):
        """It should not Create an Order without a customer ID"""
        resp = self.client.post("/orders", json={})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.all(), [])

    def test_create_order_with_invalid_customer_id(self):
        """It should not Create an Order with an invalid customer ID"""
        resp = self.client.post("/orders", json={"customer_id": "invalid"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.all(), [])

    def test_create_order_with_boolean_customer_id(self):
        """It should not Create an Order with a boolean customer ID"""
        resp = self.client.post("/orders", json={"customer_id": True})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.all(), [])

    def test_create_order_with_items(self):
        """It should Create an Order containing Items"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 456, "quantity": 2, "unit_price": 10.50},
                {"product_id": 789, "quantity": 1, "unit_price": 5.25},
            ],
        }

        resp = self.client.post("/orders", json=payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["subtotal"], 26.25)
        self.assertEqual(data["items"][0]["order_id"], data["id"])
        self.assertEqual(data["items"][1]["order_id"], data["id"])
        self.assertEqual(len(Order.find(data["id"]).items), 2)

    def test_create_order_with_invalid_items(self):
        """It should not Create an Order when Items is not a list"""
        resp = self.client.post(
            "/orders", json={"customer_id": 123, "items": "invalid"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.all(), [])

    def test_create_order_with_malformed_json(self):
        """It should not Create an Order from malformed JSON"""
        resp = self.client.post(
            "/orders", data='{"customer_id":', content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.all(), [])

    def test_create_order_without_json(self):
        """It should not Create an Order without JSON content"""
        resp = self.client.post(
            "/orders", data="customer_id=123", content_type="text/plain"
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(Order.all(), [])

    ######################################################################
    #  L I S T   O R D E R S
    ######################################################################

    def _create_orders(self, count: int) -> list:
        """Factory method to create orders in the database"""
        orders = []
        for _ in range(count):
            order = OrderFactory()
            ItemFactory(order=order)
            order.create()
            orders.append(order)
        return orders

    def test_list_all_orders(self):
        """It should list all Orders"""
        orders = self._create_orders(5)
        resp = self.client.get("/orders")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)
        returned_ids = sorted(order["id"] for order in data)
        self.assertEqual(returned_ids, sorted(order.id for order in orders))

    def test_list_orders_contents(self):
        """It should return each Order as JSON with its Items"""
        order = self._create_orders(1)[0]
        resp = self.client.get("/orders")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        returned = data[0]
        self.assertEqual(returned["id"], order.id)
        self.assertEqual(returned["customer_id"], order.customer_id)
        self.assertEqual(returned["status"], order.status.name)
        self.assertEqual(len(returned["items"]), 1)
        self.assertEqual(returned["items"][0]["order_id"], order.id)

    def test_list_orders_empty(self):
        """It should return an empty list when there are no Orders"""
        resp = self.client.get("/orders")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ######################################################################
    #  D E L E T E   O R D E R S
    ######################################################################

    def test_delete_order_with_items(self):
        """It should delete only the requested Order and all its Items"""
        order = OrderFactory()
        ItemFactory(order=order)
        ItemFactory(order=order)
        order.create()
        other_order = self._create_orders(1)[0]
        order_id = order.id
        item_ids = [item.id for item in order.items]
        other_order_id = other_order.id
        other_item_ids = [item.id for item in other_order.items]
        db.session.remove()

        resp = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")
        db.session.remove()
        self.assertIsNone(Order.find(order_id))
        for item_id in item_ids:
            self.assertIsNone(Item.find(item_id))
        self.assertEqual([order.id for order in Order.all()], [other_order_id])
        self.assertEqual([item.id for item in Item.all()], other_item_ids)
        self.assertEqual(Item.find(other_item_ids[0]).order_id, other_order_id)

    def test_delete_empty_order(self):
        """It should delete an empty Order with a 204 and an empty body"""
        order = OrderFactory()
        order.create()
        order_id = order.id
        db.session.remove()

        resp = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")
        db.session.remove()
        self.assertIsNone(Order.find(order_id))
        self.assertEqual(Item.all(), [])

    def test_delete_missing_order(self):
        """It should return a JSON 404 for a missing Order and preserve existing data"""
        order = self._create_orders(1)[0]
        order_id, item_id = order.id, order.items[0].id

        resp = self.client.delete("/orders/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertIn("Order with id [0] was not found", data["error"]["message"])
        db.session.remove()
        self.assertIsNotNone(Order.find(order_id))
        self.assertEqual(Item.find(item_id).order_id, order_id)

    def test_delete_order_twice(self):
        """It should return a JSON 404 when deleting an Order a second time"""
        order = OrderFactory()
        order.create()
        order_id = order.id

        resp = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")
        resp = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertIn(f"Order with id [{order_id}] was not found", data["error"]["message"])

    ######################################################################
    #  D E L E T E   O R D E R   I T E M S
    ######################################################################

    def _assert_delete_item_not_found(self, resp, message):
        """Checks that a missing Order or Item returns the common JSON error"""
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertIn(message, data["error"]["message"])

    def test_delete_item_preserves_order_and_other_items(self):
        """It should delete only the requested Item and recalculate its Order's subtotal"""
        order = OrderFactory()
        item = ItemFactory(order=order, quantity=2, unit_price=Decimal("8.25"))
        sibling = ItemFactory(order=order, quantity=3, unit_price=Decimal("4.25"))
        order.create()
        other_order = self._create_orders(1)[0]
        other_data = other_order.serialize()
        order_id, item_id, sibling_id = order.id, item.id, sibling.id
        other_order_id = other_order.id
        self.assertEqual(order.subtotal, Decimal("29.25"))
        db.session.remove()

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")
        db.session.remove()
        self.assertIsNone(Item.find(item_id))
        found = Order.find(order_id)
        self.assertIsNotNone(found)
        self.assertEqual([item.id for item in found.items], [sibling_id])
        self.assertEqual(found.subtotal, Decimal("12.75"))
        self.assertEqual(Order.find(other_order_id).serialize(), other_data)
        self.assertEqual(len(Order.all()), 2)
        self.assertEqual(len(Item.all()), 2)

    def test_delete_last_item_keeps_empty_order(self):
        """It should keep an empty Order with zero subtotal after deleting its last Item"""
        order = self._create_orders(1)[0]
        order_id, item_id = order.id, order.items[0].id
        db.session.remove()

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")
        db.session.remove()
        self.assertIsNone(Item.find(item_id))
        found = Order.find(order_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.items, [])
        self.assertEqual(found.subtotal, Decimal("0.00"))

    def test_delete_item_missing_order(self):
        """It should return a JSON 404 when the Order does not exist and preserve the Item"""
        order = self._create_orders(1)[0]
        order_id, item_id = order.id, order.items[0].id
        data = order.serialize()

        resp = self.client.delete(f"/orders/0/items/{item_id}")
        self._assert_delete_item_not_found(resp, "Order with id [0] was not found")
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), data)
        self.assertEqual(Item.find(item_id).order_id, order_id)

    def test_delete_item_missing_item(self):
        """It should return a JSON 404 when the Item does not exist and preserve the Order"""
        order = self._create_orders(1)[0]
        order_id = order.id
        missing_item_id = order.items[0].id + 100000
        data = order.serialize()

        resp = self.client.delete(f"/orders/{order_id}/items/{missing_item_id}")
        self._assert_delete_item_not_found(
            resp, f"Item with id [{missing_item_id}] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), data)

    def test_delete_item_from_wrong_order(self):
        """It should reject an Item belonging to a different Order without changing either"""
        orders = self._create_orders(2)
        order, other_order = orders[0], orders[1]
        order_id, other_order_id = order.id, other_order.id
        item_id = other_order.items[0].id
        data, other_data = order.serialize(), other_order.serialize()

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self._assert_delete_item_not_found(
            resp, f"Item with id [{item_id}] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), data)
        self.assertEqual(Order.find(other_order_id).serialize(), other_data)
        self.assertEqual(Item.find(item_id).order_id, other_order_id)

    def test_delete_item_twice(self):
        """It should return a JSON 404 on repeated deletion and keep the Order"""
        order = self._create_orders(1)[0]
        order_id, item_id = order.id, order.items[0].id
        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self._assert_delete_item_not_found(
            resp, f"Item with id [{item_id}] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertIsNotNone(Order.find(order_id))
        self.assertEqual(Order.find(order_id).items, [])

    ######################################################################
    #  R E A D   A N   O R D E R   I T E M
    ######################################################################

    def _assert_read_item_not_found(self, resp, message):
        """Checks the common JSON response for an Item lookup that cannot be resolved"""
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertIn(message, data["error"]["message"])

    def test_read_order_item(self):
        """It should return the requested Item's fields without changing any data"""
        order = OrderFactory()
        item = ItemFactory(order=order, product_id=123, quantity=3, unit_price=Decimal("2.35"))
        ItemFactory(order=order)
        order.create()
        other_order = self._create_orders(1)[0]
        order_id, item_id, other_order_id = order.id, item.id, other_order.id
        before, other_before = order.serialize(), other_order.serialize()
        db.session.remove()

        resp = self.client.get(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        self.assertEqual(
            resp.get_json(),
            {"id": item_id, "order_id": order_id, "product_id": 123,
             "quantity": 3, "unit_price": 2.35, "line_total": 7.05},
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), before)
        self.assertEqual(Order.find(other_order_id).serialize(), other_before)
        self.assertEqual(len(Order.all()), 2)
        self.assertEqual(len(Item.all()), 3)

    def test_read_item_missing_order(self):
        """It should return JSON 404 when the parent Order does not exist"""
        order = self._create_orders(1)[0]
        order_id, item_id = order.id, order.items[0].id
        before = order.serialize()

        resp = self.client.get(f"/orders/0/items/{item_id}")
        self._assert_read_item_not_found(resp, "Order with id [0] was not found")
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), before)

    def test_read_item_missing_item(self):
        """It should return JSON 404 when the Item does not exist"""
        order = self._create_orders(1)[0]
        order_id = order.id
        before = order.serialize()

        resp = self.client.get(f"/orders/{order_id}/items/0")
        self._assert_read_item_not_found(
            resp, f"Item with id [0] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), before)

    def test_read_item_from_empty_order(self):
        """It should return JSON 404 for an empty Order without changing it"""
        order = OrderFactory()
        order.create()
        order_id = order.id
        before = order.serialize()

        resp = self.client.get(f"/orders/{order_id}/items/0")
        self._assert_read_item_not_found(
            resp, f"Item with id [0] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), before)

    def test_read_item_from_wrong_order(self):
        """It should not expose an Item through a different Order's URL"""
        orders = self._create_orders(2)
        order, other_order = orders[0], orders[1]
        order_id, other_order_id, item_id = order.id, other_order.id, other_order.items[0].id
        before, other_before = order.serialize(), other_order.serialize()

        resp = self.client.get(f"/orders/{order_id}/items/{item_id}")
        self._assert_read_item_not_found(
            resp, f"Item with id [{item_id}] was not found in Order with id [{order_id}]"
        )
        db.session.remove()
        self.assertEqual(Order.find(order_id).serialize(), before)
        self.assertEqual(Order.find(other_order_id).serialize(), other_before)
