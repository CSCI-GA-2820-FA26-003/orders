"""
Item Model

An Item is a single line of an Order: a product, how many, and at what price
"""

import logging
from decimal import Decimal, InvalidOperation
from .persistent_base import db, PersistentBase, DataValidationError

logger = logging.getLogger("flask.app")

MIN_QUANTITY = 1
MAX_QUANTITY = 999


######################################################################
#  I T E M   M O D E L
######################################################################
class Item(db.Model, PersistentBase):
    """
    Class that represents an Item
    """

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("order.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<Item product_id=[{self.product_id}] id=[{self.id}] order[{self.order_id}]>"

    @property
    def line_total(self) -> Decimal:
        """The price of this line: quantity x unit_price"""
        return Decimal(self.quantity) * Decimal(self.unit_price)

    def serialize(self) -> dict:
        """Converts an Item into a dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "line_total": float(self.line_total),
        }

    def deserialize(self, data: dict):
        """
        Populates an Item from a dictionary

        Args:
            data (dict): A dictionary containing the resource data
        """
        try:
            self.product_id = _to_int(data["product_id"], "product_id")
            self.quantity = _to_int(data["quantity"], "quantity")
            if not MIN_QUANTITY <= self.quantity <= MAX_QUANTITY:
                raise DataValidationError(
                    f"Invalid Item: quantity must be between {MIN_QUANTITY} and {MAX_QUANTITY}"
                )
            self.unit_price = _to_price(data["unit_price"])
            self.order_id = data.get("order_id")
        except KeyError as error:
            raise DataValidationError(
                "Invalid Item: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid Item: body of request contained bad or no data "
                + str(error)
            ) from error
        return self


######################################################################
#  H E L P E R   F U N C T I O N S
######################################################################
def _to_int(value, field: str) -> int:
    """Makes sure a value is a real integer (bool is not allowed)"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataValidationError(f"Invalid type for {field}: {type(value).__name__}")
    return value


def _to_price(value) -> Decimal:
    """Converts a number or numeric string into a non-negative Decimal price"""
    if isinstance(value, bool):
        raise DataValidationError("Invalid type for unit_price: bool")
    try:
        price = Decimal(str(value))
    except InvalidOperation as error:
        raise DataValidationError(f"Invalid unit_price: {value}") from error
    if not price.is_finite() or price < 0:
        raise DataValidationError(f"Invalid unit_price: {value}")
    return price
