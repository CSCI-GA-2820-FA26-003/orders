Feature: The Orders admin page
    As an eCommerce administrator
    I need a web page for managing orders
    So that I can work with orders without calling the API directly

Scenario: The admin page is running
    When I open the Orders admin page
    Then I see the Orders heading

Scenario: Get an order ID after creating an order
    Given I am on the Orders admin page
    When I submit the details for a new order
    Then I see a creation confirmation and the new order ID

Scenario: Forget the customer ID
    Given I am on the Orders admin page
    When I submit a new order without a customer ID
    Then I see a message explaining what is wrong
    And no order ID is shown
