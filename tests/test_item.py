"""
Test cases for Item Model
"""

# pylint: disable=duplicate-code
import os
import logging
from decimal import Decimal
from unittest import TestCase
from wsgi import app
from service.models import Order, Item, DataValidationError, db
from tests.factories import OrderFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


######################################################################
#  I T E M   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestItem(TestCase):
    """Test Cases for Item Model"""

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

    def test_add_order_item(self):
        """It should add an Item to an existing Order"""
        order = OrderFactory()
        item = ItemFactory(order=order)
        order.create()

        new_order = Order.find(order.id)
        self.assertEqual(len(new_order.items), 1)
        self.assertEqual(new_order.items[0].product_id, item.product_id)

        item2 = ItemFactory(order=order)
        order.items.append(item2)
        order.update()

        new_order = Order.find(order.id)
        self.assertEqual(len(new_order.items), 2)
        self.assertEqual(new_order.items[1].product_id, item2.product_id)
        self.assertEqual(str(item2), f"<Item product_id=[{item2.product_id}] id=[{item2.id}] order[{order.id}]>")

    def test_read_order_item(self):
        """It should Read an Item by its id"""
        order = OrderFactory()
        item = ItemFactory(order=order)
        order.create()

        found = Item.find(item.id)
        self.assertEqual(found.order_id, order.id)
        self.assertEqual(found.product_id, item.product_id)
        self.assertEqual(found.quantity, item.quantity)
        self.assertEqual(found.unit_price, item.unit_price)

    def test_update_order_item(self):
        """It should Update an Item of an Order"""
        order = OrderFactory()
        ItemFactory(order=order, quantity=1)
        order.create()

        order = Order.find(order.id)
        item = order.items[0]
        item.quantity = 5
        item.update()

        order = Order.find(order.id)
        self.assertEqual(order.items[0].quantity, 5)

    def test_delete_order_item(self):
        """It should Delete an Item from an Order"""
        order = OrderFactory()
        ItemFactory(order=order)
        order.create()

        order = Order.find(order.id)
        item = order.items[0]
        item.delete()

        order = Order.find(order.id)
        self.assertEqual(len(order.items), 0)
        self.assertEqual(len(Order.all()), 1)

    def test_create_item_without_order(self):
        """It should not Create an Item that does not belong to an Order"""
        item = Item(product_id=1, quantity=1, unit_price=Decimal("1.00"))  # pylint: disable=unexpected-keyword-arg
        self.assertRaises(DataValidationError, item.create)

    def test_create_item_with_bad_quantity(self):
        """It should not Create an Item with a quantity out of range"""
        for quantity in [0, 1000]:
            order = OrderFactory()
            ItemFactory(order=order, quantity=quantity)
            self.assertRaises(DataValidationError, order.create)
        self.assertEqual(Item.all(), [])

    def test_update_item_with_bad_quantity(self):
        """It should not Update an Item with a quantity out of range"""
        order = OrderFactory()
        ItemFactory(order=order, quantity=1)
        order.create()
        item = Order.find(order.id).items[0]
        item.quantity = 1000
        self.assertRaises(DataValidationError, item.update)
        self.assertEqual(Item.find(item.id).quantity, 1)

    def test_update_item_keeps_order(self):
        """It should keep the Order of an Item when order_id is not given"""
        order = OrderFactory()
        ItemFactory(order=order)
        order.create()
        item = Order.find(order.id).items[0]
        item.deserialize({"product_id": 7, "quantity": 2, "unit_price": "3.50"})
        item.update()
        found = Item.find(item.id)
        self.assertEqual(found.order_id, order.id)
        self.assertEqual(found.product_id, 7)
        self.assertEqual(found.quantity, 2)

    def test_price_saved_without_change(self):
        """It should Save and Reload a unit_price without changing it"""
        order = OrderFactory()
        item = Item().deserialize({"product_id": 1, "quantity": 3, "unit_price": "1.23"})
        order.items.append(item)
        order.create()
        found = Item.find(item.id)
        self.assertEqual(found.unit_price, Decimal("1.23"))
        self.assertEqual(found.line_total, Decimal("3.69"))

    def test_line_total(self):
        """It should calculate the line total as quantity x unit_price"""
        item = ItemFactory(quantity=3, unit_price=Decimal("19.99"))
        self.assertEqual(item.line_total, Decimal("59.97"))

    def test_serialize_an_order_item(self):
        """It should Serialize an Item"""
        item = ItemFactory(quantity=2, unit_price=Decimal("5.25"))
        data = item.serialize()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["order_id"], item.order_id)
        self.assertEqual(data["product_id"], item.product_id)
        self.assertEqual(data["quantity"], 2)
        self.assertEqual(data["unit_price"], 5.25)
        self.assertEqual(data["line_total"], 10.5)

    def test_deserialize_an_order_item(self):
        """It should Deserialize an Item"""
        order = OrderFactory()
        item = ItemFactory(order=order)
        order.create()
        new_item = Item().deserialize(item.serialize())
        self.assertEqual(new_item.order_id, order.id)
        self.assertEqual(new_item.product_id, item.product_id)
        self.assertEqual(new_item.quantity, item.quantity)
        self.assertEqual(new_item.unit_price, item.unit_price)

    def test_deserialize_price_bounds(self):
        """It should Deserialize a unit_price of 0 or the largest allowed value"""
        for price in ["0", "99999999.99", 19.99, 5]:
            data = {"product_id": 1, "quantity": 1, "unit_price": price}
            self.assertEqual(Item().deserialize(data).unit_price, Decimal(str(price)))

    def test_deserialize_price_as_string(self):
        """It should Deserialize a unit_price given as a string"""
        data = {"product_id": 1, "quantity": 1, "unit_price": "12.34"}
        item = Item().deserialize(data)
        self.assertEqual(item.unit_price, Decimal("12.34"))
        self.assertIsNone(item.order_id)

    def test_deserialize_missing_field(self):
        """It should not Deserialize an Item with a missing field"""
        item = Item()
        self.assertRaises(DataValidationError, item.deserialize, {})
        self.assertRaises(DataValidationError, item.deserialize, {"product_id": 1, "quantity": 1})

    def test_deserialize_bad_product_id(self):
        """It should not Deserialize an Item with a bad product_id"""
        item = Item()
        data = {"product_id": "abc", "quantity": 1, "unit_price": 1.00}
        self.assertRaises(DataValidationError, item.deserialize, data)

    def test_deserialize_bad_quantity(self):
        """It should not Deserialize an Item with a quantity out of range"""
        item = Item()
        for quantity in [0, -1, 1000, 2.5, True]:
            data = {"product_id": 1, "quantity": quantity, "unit_price": 1.00}
            self.assertRaises(DataValidationError, item.deserialize, data)

    def test_deserialize_quantity_bounds(self):
        """It should Deserialize an Item with quantity of 1 or 999"""
        for quantity in [1, 999]:
            data = {"product_id": 1, "quantity": quantity, "unit_price": 1.00}
            self.assertEqual(Item().deserialize(data).quantity, quantity)

    def test_deserialize_bad_price(self):
        """It should not Deserialize an Item with a bad unit_price"""
        item = Item()
        for price in ["abc", -1, "NaN", "Infinity", True, None, "1.234", 0.001, "100000000.00"]:
            data = {"product_id": 1, "quantity": 1, "unit_price": price}
            self.assertRaises(DataValidationError, item.deserialize, data)

    def test_deserialize_with_type_error(self):
        """It should not Deserialize an Item with a TypeError"""
        item = Item()
        self.assertRaises(DataValidationError, item.deserialize, [])
