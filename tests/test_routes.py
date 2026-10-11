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
