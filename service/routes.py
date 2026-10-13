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
Order Service

This service implements a REST API that allows you to Create, Read, Update
and Delete Orders
"""

from flask import jsonify, request, url_for, abort
from flask import current_app as app  # Import Flask application
from service.models import Order, Item  # noqa: F401 pylint: disable=unused-import
from service.common import status  # HTTP Status Codes


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    return (
        "Reminder: return some useful information in json format about the service here",
        status.HTTP_200_OK,
    )


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
# CREATE AN ORDER
######################################################################
@app.route("/orders", methods=["POST"])
def create_order():
    """Creates a new Order"""
    app.logger.info("Request to create an Order")

    if not request.is_json:
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            description="Content-Type must be application/json",
        )

    order = Order()
    order.deserialize(request.get_json())
    order.create()

    location_url = f'{url_for("list_orders", _external=True)}/{order.id}'
    return jsonify(order.serialize()), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# LIST ALL ORDERS
######################################################################
@app.route("/orders", methods=["GET"])
def list_orders():
    """Returns all of the Orders"""
    app.logger.info("Request for order list")

    orders = Order.all()

    results = [order.serialize() for order in orders]
    app.logger.info("Returning %d orders", len(results))
    return jsonify(results), status.HTTP_200_OK


######################################################################
# DELETE AN ORDER
######################################################################
@app.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    """Deletes an Order and its Items, returning no content"""
    app.logger.info("Request to delete Order with id: %s", order_id)
    order = Order.find(order_id)
    if order is None:
        abort(
            status.HTTP_404_NOT_FOUND,
            description=f"Order with id [{order_id}] was not found",
        )

    order.delete()
    app.logger.info("Order with id: %s deleted", order_id)
    return "", status.HTTP_204_NO_CONTENT
