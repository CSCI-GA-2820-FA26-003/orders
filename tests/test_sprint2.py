"""Tests for Sprint 2 order cancellation and service health."""

# pylint: disable=duplicate-code
from unittest import TestCase
from unittest.mock import patch
from wsgi import app
from service.models import db, Order, Item, OrderStatus, DataValidationError
from service.models.order import InvalidOrderStateError
from tests.factories import OrderFactory, ItemFactory


class TestSprint2(TestCase):
    """Verify action transitions, persistence, errors and health responses."""

    def setUp(self):
        """Use the isolated database selected by DATABASE_URI."""
        self.context = app.app_context()
        self.context.push()
        db.session.query(Item).delete()
        db.session.query(Order).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Release the database session and Flask context."""
        db.session.remove()
        self.context.pop()

    def test_health(self):
        """It should return the exact liveness response without a database query."""
        with patch.object(Order, "all", side_effect=AssertionError("Unexpected database query")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.get_json(), {"status": "OK"})

    def test_cancel_order_persists_and_preserves_items(self):
        """It should cancel a NEW order and preserve its items and other orders."""
        order = OrderFactory(status=OrderStatus.NEW)
        item = ItemFactory(order=order)
        order.create()
        other = OrderFactory(status=OrderStatus.NEW)
        other.create()
        order_id, other_id, item_id = order.id, other.id, item.id
        original = order.serialize()
        response = self.client.put(f"/orders/{order_id}/cancel")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "CANCELLED")
        self.assertEqual(response.get_json()["items"], original["items"])
        self.assertEqual(response.get_json()["subtotal"], original["subtotal"])
        self.assertEqual(response.get_json()["customer_id"], original["customer_id"])
        db.session.remove()
        self.assertEqual(Order.find(order_id).status, OrderStatus.CANCELLED)
        self.assertEqual(Item.find(item_id).order_id, order_id)
        self.assertEqual(Order.find(other_id).status, OrderStatus.NEW)
        self.assertEqual(self.client.get(f"/orders/{order_id}").get_json()["status"], "CANCELLED")

    def test_repeated_cancellation_is_a_no_op(self):
        """It should return an already-cancelled order without issuing an update."""
        order = OrderFactory(status=OrderStatus.CANCELLED)
        order.create()
        original = order.serialize()
        with patch.object(Order, "update") as update_mock:
            response = self.client.put(f"/orders/{order.id}/cancel")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), original)
        update_mock.assert_not_called()

    def test_cannot_cancel_shipped_or_delivered_orders(self):
        """It should reject forbidden transitions with a consistent JSON conflict."""
        for order_status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            with self.subTest(status=order_status):
                order = OrderFactory(status=order_status)
                order.create()
                original = order.serialize()
                response = self.client.put(f"/orders/{order.id}/cancel")
                self.assertEqual(response.status_code, 409)
                self.assertEqual(set(response.get_json()), {"status", "error", "message"})
                self.assertEqual(response.get_json()["status"], 409)
                self.assertEqual(Order.find(order.id).serialize(), original)
                self.assertRaises(InvalidOrderStateError, order.cancel)

    def test_cancel_order_not_found(self):
        """It should return a JSON 404 for an order that does not exist."""
        response = self.client.put("/orders/0/cancel")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(set(response.get_json()), {"status", "error", "message"})
        self.assertEqual(response.get_json()["status"], 404)

    def test_cancel_model_rolls_back_database_failure(self):
        """It should leave the persisted order NEW when its commit fails."""
        order = OrderFactory(status=OrderStatus.NEW)
        order.create()
        order_id = order.id
        with patch("service.models.db.session.commit", side_effect=Exception("test failure")):
            self.assertRaises(DataValidationError, order.cancel)
        db.session.remove()
        self.assertEqual(Order.find(order_id).status, OrderStatus.NEW)

    def test_cancel_empty_order(self):
        """It should allow cancelling an order without any items."""
        order = OrderFactory(status=OrderStatus.NEW)
        order.create()
        order.cancel()
        order_id = order.id
        db.session.remove()
        found = Order.find(order_id)
        self.assertEqual(found.status, OrderStatus.CANCELLED)
        self.assertEqual(found.items, [])
