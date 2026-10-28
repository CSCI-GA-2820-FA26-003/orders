"""Model and API acceptance checks for status filtering (stories 36-38)."""

# pylint: disable=duplicate-code
from unittest import TestCase
from urllib.parse import urlencode
from wsgi import app
from service.models import db, Order, Item, OrderStatus
from tests.factories import OrderFactory, ItemFactory


class TestOrderFiltering(TestCase):
    """Verify filtering with mixed states and consistent query errors."""

    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        db.session.query(Item).delete()
        db.session.query(Order).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        self.context.pop()

    def test_model_filters_each_status(self):
        """Model queries return only matching rows from a mixed collection."""
        expected = {}
        for order_status in OrderStatus:
            expected[order_status] = set()
            for _ in range(2):
                order = OrderFactory(status=order_status)
                order.create()
                expected[order_status].add(order.id)
        db.session.remove()
        for order_status in OrderStatus:
            with self.subTest(status=order_status):
                found = Order.find_by_status(order_status)
                self.assertEqual({order.id for order in found}, expected[order_status])
                self.assertTrue(all(order.status == order_status for order in found))

    def test_model_returns_no_matches(self):
        """A valid status with no matching orders returns an empty list."""
        OrderFactory(status=OrderStatus.NEW).create()
        self.assertEqual(Order.find_by_status(OrderStatus.CANCELLED), [])

    def test_model_filters_empty_database(self):
        """An empty table produces an empty result."""
        self.assertEqual(Order.find_by_status(OrderStatus.NEW), [])

    def test_api_filters_mixed_statuses(self):
        """API filtering excludes other states, even when they also exist."""
        expected = {}
        for order_status in OrderStatus:
            order = OrderFactory(status=order_status)
            order.create()
            expected[order_status] = order.id
        for order_status in OrderStatus:
            with self.subTest(status=order_status):
                response = self.client.get("/orders", query_string={"status": order_status.name})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([order["id"] for order in response.get_json()], [expected[order_status]])
                self.assertEqual(response.get_json()[0]["status"], order_status.name)

    def test_api_without_filter_returns_all_orders(self):
        """Omitting the query returns orders in every state."""
        expected = set()
        for order_status in OrderStatus:
            order = OrderFactory(status=order_status)
            order.create()
            expected.add(order.id)
        response = self.client.get("/orders")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({order["id"] for order in response.get_json()}, expected)

    def test_api_returns_no_matches(self):
        """A valid filter with no matches returns 200 and an empty JSON list."""
        OrderFactory(status=OrderStatus.NEW).create()
        response = self.client.get("/orders?status=CANCELLED")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_api_rejects_invalid_status(self):
        """Empty, unsupported and incorrectly cased statuses use JSON 400 errors."""
        for value in ("", "pending", "new", "unknown", " NEW "):
            with self.subTest(value=value):
                response = self.client.get("/orders?" + urlencode({"status": value}))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(set(response.get_json()), {"status", "error", "message"})
                self.assertEqual(response.get_json()["status"], 400)

    def test_api_rejects_unsupported_parameters(self):
        """Unknown query keys are rejected, including alongside a valid status."""
        for query in ("foo=1", "status=NEW&foo=1", "bar=2&foo=1"):
            with self.subTest(query=query):
                response = self.client.get("/orders?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(set(response.get_json()), {"status", "error", "message"})
                self.assertEqual(response.get_json()["status"], 400)

    def test_api_rejects_repeated_status(self):
        """Repeated filters are rejected rather than silently taking one value."""
        for query in ("status=NEW&status=SHIPPED", "status=NEW&status=NEW"):
            with self.subTest(query=query):
                response = self.client.get("/orders?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["status"], 400)

    def test_filter_preserves_order_and_item_data(self):
        """Querying does not change persisted status, items or totals."""
        order = OrderFactory(status=OrderStatus.NEW)
        ItemFactory(order=order)
        order.create()
        original = order.serialize()
        OrderFactory(status=OrderStatus.SHIPPED).create()
        response = self.client.get("/orders?status=NEW")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [original])
        db.session.remove()
        self.assertEqual(Order.find(order.id).serialize(), original)
        self.assertEqual(Order.query.count(), 2)
