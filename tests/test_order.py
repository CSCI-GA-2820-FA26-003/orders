"""
Test cases for Order Model
"""

# pylint: disable=duplicate-code
import os
import logging
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch
from wsgi import app
from service.models import Order, Item, OrderStatus, DataValidationError, db
from tests.factories import OrderFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


######################################################################
#  O R D E R   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestOrder(TestCase):
    """Test Cases for Order Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Item).delete()  # clean up the last tests
        db.session.query(Order).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_an_order(self):
        """It should Create an Order and assert that it exists"""
        fake_order = OrderFactory()
        # pylint: disable=unexpected-keyword-arg
        order = Order(customer_id=fake_order.customer_id, status=fake_order.status)
        self.assertIsNotNone(order)
        self.assertEqual(order.id, None)
        self.assertEqual(order.customer_id, fake_order.customer_id)
        self.assertEqual(order.status, fake_order.status)
        self.assertEqual(str(order), f"<Order customer_id=[{fake_order.customer_id}] id=[None]>")

    def test_add_an_order(self):
        """It should Create an Order and add it to the database"""
        orders = Order.all()
        self.assertEqual(orders, [])
        order = OrderFactory()
        order.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(order.id)
        orders = Order.all()
        self.assertEqual(len(orders), 1)
        # Timestamps are set by the database
        self.assertIsNotNone(orders[0].created_at)
        self.assertIsNotNone(orders[0].updated_at)

    def test_default_status_is_new(self):
        """It should default the status of a new Order to NEW"""
        order = Order(customer_id=1)  # pylint: disable=unexpected-keyword-arg
        order.create()
        found = Order.find(order.id)
        self.assertEqual(found.status, OrderStatus.NEW)

    def test_add_an_order_with_items(self):
        """It should Create an Order with Items and give each a unique id"""
        order = OrderFactory()
        item1 = ItemFactory(order=order)
        item2 = ItemFactory(order=order)
        order.create()
        self.assertIsNotNone(order.id)

        found = Order.find(order.id)
        self.assertEqual(len(found.items), 2)
        self.assertIsNotNone(found.items[0].id)
        self.assertIsNotNone(found.items[1].id)
        self.assertNotEqual(found.items[0].id, found.items[1].id)
        self.assertEqual(found.items[0].order_id, order.id)
        self.assertEqual(found.items[0].product_id, item1.product_id)
        self.assertEqual(found.items[1].product_id, item2.product_id)

    @patch("service.models.db.session.commit")
    def test_add_order_failed(self, exception_mock):
        """It should not Create an Order on database error"""
        exception_mock.side_effect = Exception()
        order = OrderFactory()
        self.assertRaises(DataValidationError, order.create)

    def test_read_an_order(self):
        """It should Read an Order"""
        order = OrderFactory()
        order.create()

        found = Order.find(order.id)
        self.assertEqual(found.id, order.id)
        self.assertEqual(found.customer_id, order.customer_id)
        self.assertEqual(found.status, order.status)
        self.assertEqual(found.items, [])

    def test_read_order_not_found(self):
        """It should return None when an Order is not found"""
        self.assertIsNone(Order.find(0))

    def test_update_an_order(self):
        """It should Update an Order"""
        order = OrderFactory(status=OrderStatus.NEW)
        order.create()
        self.assertIsNotNone(order.id)

        # Fetch it back and change it
        order = Order.find(order.id)
        order.status = OrderStatus.SHIPPED
        order.update()

        # Fetch it back again
        order = Order.find(order.id)
        self.assertEqual(order.status, OrderStatus.SHIPPED)
        self.assertEqual(len(Order.all()), 1)

    def test_update_order_without_id(self):
        """It should not Update an Order that has no id"""
        order = OrderFactory()
        order.id = None
        self.assertRaises(DataValidationError, order.update)

    def test_update_order_failed(self):
        """It should not Update an Order on database error"""
        order = OrderFactory(status=OrderStatus.NEW)
        order.create()
        order.status = OrderStatus.CANCELLED
        with patch("service.models.db.session.commit") as commit_mock:
            commit_mock.side_effect = Exception()
            self.assertRaises(DataValidationError, order.update)
            commit_mock.assert_called_once()
        # the change should have been rolled back
        self.assertEqual(Order.find(order.id).status, OrderStatus.NEW)

    def test_delete_an_order(self):
        """It should Delete an Order from the database"""
        order = OrderFactory()
        order.create()
        self.assertEqual(len(Order.all()), 1)
        order.delete()
        self.assertEqual(len(Order.all()), 0)

    def test_delete_order_deletes_items(self):
        """It should Delete the Items of an Order when the Order is deleted"""
        order = OrderFactory()
        ItemFactory(order=order)
        ItemFactory(order=order)
        order.create()
        self.assertEqual(len(Item.all()), 2)

        order.delete()
        self.assertEqual(len(Order.all()), 0)
        self.assertEqual(len(Item.all()), 0)

    def test_delete_order_failed(self):
        """It should not Delete an Order on database error"""
        order = OrderFactory()
        order.create()
        with patch("service.models.db.session.commit") as commit_mock:
            commit_mock.side_effect = Exception()
            self.assertRaises(DataValidationError, order.delete)
            commit_mock.assert_called_once()
        # the Order should still be in the database
        self.assertIsNotNone(Order.find(order.id))

    def test_list_all_orders(self):
        """It should List all Orders in the database"""
        self.assertEqual(Order.all(), [])
        for order in OrderFactory.create_batch(5):
            order.create()
        self.assertEqual(len(Order.all()), 5)

    def test_find_by_customer_id(self):
        """It should Find Orders by customer_id"""
        orders = OrderFactory.create_batch(3, customer_id=1)
        orders.append(OrderFactory(customer_id=2))
        for order in orders:
            order.create()

        found = Order.find_by_customer_id(1)
        self.assertEqual(len(found), 3)
        for order in found:
            self.assertEqual(order.customer_id, 1)
        self.assertEqual(len(Order.find_by_customer_id(2)), 1)
        self.assertEqual(Order.find_by_customer_id(3), [])

    def test_subtotal(self):
        """It should calculate the subtotal from its Items"""
        order = OrderFactory()
        self.assertEqual(order.subtotal, Decimal("0.00"))
        ItemFactory(order=order, quantity=2, unit_price=Decimal("10.50"))
        ItemFactory(order=order, quantity=1, unit_price=Decimal("3.25"))
        self.assertEqual(order.subtotal, Decimal("24.25"))

    def test_serialize_an_order(self):
        """It should Serialize an Order with its Items"""
        order = OrderFactory()
        item = ItemFactory(order=order)
        order.create()
        data = order.serialize()
        self.assertEqual(data["id"], order.id)
        self.assertEqual(data["customer_id"], order.customer_id)
        self.assertEqual(data["status"], order.status.name)
        self.assertEqual(data["subtotal"], float(item.line_total))
        self.assertEqual(data["created_at"], order.created_at.isoformat())
        self.assertEqual(data["updated_at"], order.updated_at.isoformat())
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], item.id)
        self.assertEqual(data["items"][0]["order_id"], order.id)
        self.assertEqual(data["items"][0]["product_id"], item.product_id)

    def test_serialize_a_new_order(self):
        """It should Serialize an Order that has not been saved yet"""
        order = Order(customer_id=5)  # pylint: disable=unexpected-keyword-arg
        data = order.serialize()
        self.assertEqual(data["customer_id"], 5)
        self.assertEqual(data["status"], "NEW")
        self.assertEqual(data["subtotal"], 0.0)
        self.assertIsNone(data["created_at"])
        self.assertIsNone(data["updated_at"])
        self.assertEqual(data["items"], [])

    def test_deserialize_an_order(self):
        """It should Deserialize an Order with its Items"""
        order = OrderFactory()
        ItemFactory(order=order)
        order.create()
        new_order = Order()
        new_order.deserialize(order.serialize())
        self.assertEqual(new_order.customer_id, order.customer_id)
        self.assertEqual(new_order.status, order.status)
        self.assertEqual(len(new_order.items), 1)
        self.assertEqual(new_order.items[0].product_id, order.items[0].product_id)
        self.assertEqual(new_order.items[0].quantity, order.items[0].quantity)
        self.assertEqual(new_order.items[0].unit_price, order.items[0].unit_price)

    def test_deserialize_default_status(self):
        """It should Deserialize an Order with no status as NEW"""
        order = Order().deserialize({"customer_id": 7})
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertEqual(order.items, [])

    def test_deserialize_missing_customer_id(self):
        """It should not Deserialize an Order without a customer_id"""
        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, {"status": "NEW"})

    def test_deserialize_bad_customer_id(self):
        """It should not Deserialize an Order with a bad customer_id"""
        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, {"customer_id": "abc"})
        self.assertRaises(DataValidationError, order.deserialize, {"customer_id": True})

    def test_deserialize_bad_status(self):
        """It should not Deserialize an Order with an unknown status"""
        order = Order()
        data = {"customer_id": 1, "status": "LOST"}
        self.assertRaises(DataValidationError, order.deserialize, data)

    def test_deserialize_bad_items(self):
        """It should not Deserialize an Order with bad Items"""
        order = Order()
        data = {"customer_id": 1, "items": [{"product_id": 1}]}
        self.assertRaises(DataValidationError, order.deserialize, data)

    def test_deserialize_items_not_a_list(self):
        """It should not Deserialize an Order when items is not a list"""
        order = Order()
        for items in [{}, "", "abc", 5, None]:
            data = {"customer_id": 1, "items": items}
            self.assertRaises(DataValidationError, order.deserialize, data)

    def test_deserialize_with_type_error(self):
        """It should not Deserialize an Order with a TypeError"""
        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, [])
        self.assertRaises(DataValidationError, order.deserialize, None)

    def test_deserialize_with_bad_item_data(self):
        """It should not Deserialize an Order when an item is not a dictionary"""
        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, {"customer_id": 1, "items": [[]]})
