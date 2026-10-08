"""
Order Model

An Order belongs to a customer and holds a collection of Items
"""

import logging
from decimal import Decimal
from enum import Enum
from .persistent_base import db, PersistentBase, DataValidationError
from .item import Item, _to_int

logger = logging.getLogger("flask.app")


class OrderStatus(Enum):
    """Enumeration of the states an Order can be in"""

    NEW = "NEW"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


######################################################################
#  O R D E R   M O D E L
######################################################################
class Order(db.Model, PersistentBase):
    """
    Class that represents an Order
    """

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum(OrderStatus), nullable=False, server_default=OrderStatus.NEW.name
    )
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )
    items = db.relationship(
        "Item",
        backref="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Item.id",
    )

    def __repr__(self):
        return f"<Order customer_id=[{self.customer_id}] id=[{self.id}]>"

    @property
    def subtotal(self) -> Decimal:
        """The sum of all the line totals of the items in this Order"""
        return sum((item.line_total for item in self.items), Decimal("0.00"))

    def serialize(self) -> dict:
        """Converts an Order into a dictionary"""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "status": self.status.name if self.status else OrderStatus.NEW.name,
            "subtotal": float(self.subtotal),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [item.serialize() for item in self.items],
        }

    def deserialize(self, data: dict):
        """
        Populates an Order from a dictionary

        All of the data is validated first so that the Order is left
        unchanged if anything is invalid. When "items" is given it replaces
        the current items, otherwise the current items are kept.

        Args:
            data (dict): A dictionary containing the resource data
        """
        try:
            customer_id = _to_int(data["customer_id"], "customer_id")
            status = OrderStatus[data.get("status", OrderStatus.NEW.name)]
            # handle inner list of items
            new_items = None
            if "items" in data:
                if not isinstance(data["items"], list):
                    raise DataValidationError("Invalid Order: items must be a list")
                new_items = [Item().deserialize(json_item) for json_item in data["items"]]
        except KeyError as error:
            raise DataValidationError(
                "Invalid Order: missing or bad value " + str(error.args[0])
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid Order: body of request contained bad or no data "
                + str(error)
            ) from error

        # everything is valid so it is safe to change the Order now
        self.customer_id = customer_id
        self.status = status
        if new_items is not None:
            self.items = new_items
        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def find_by_customer_id(cls, customer_id: int):
        """Returns all Orders placed by the given customer

        Args:
            customer_id (int): the id of the customer whose Orders you want
        """
        logger.info("Processing customer_id query for %s ...", customer_id)
        return cls.query.filter(cls.customer_id == customer_id).all()
