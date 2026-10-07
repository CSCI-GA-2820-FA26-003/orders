"""
Test Factory to make fake objects for testing
"""

from factory import Factory, SubFactory, Sequence, post_generation
from factory.fuzzy import FuzzyChoice, FuzzyDecimal, FuzzyInteger
from service.models import Order, Item, OrderStatus


class OrderFactory(Factory):
    """Creates fake Orders"""

    # pylint: disable=too-few-public-methods
    class Meta:
        """Maps factory to data model"""

        model = Order

    id = Sequence(lambda n: n)
    customer_id = FuzzyInteger(1, 10000)
    status = FuzzyChoice(choices=list(OrderStatus))

    # the many side of relationships can be a little wonky in factory boy:
    # https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
    @post_generation
    def items(
        self, create, extracted, **kwargs
    ):  # pylint: disable=method-hidden, unused-argument
        """Creates the items list"""
        if not create:
            return

        if extracted:
            self.items = extracted


class ItemFactory(Factory):
    """Creates fake Items"""

    # pylint: disable=too-few-public-methods
    class Meta:
        """Maps factory to data model"""

        model = Item

    id = Sequence(lambda n: n)
    order_id = None
    product_id = FuzzyInteger(1, 10000)
    quantity = FuzzyInteger(1, 10)
    unit_price = FuzzyDecimal(0.99, 500.00, precision=2)
    order = SubFactory(OrderFactory)
