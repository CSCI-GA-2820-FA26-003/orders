Feature: The Orders admin page
    As an eCommerce administrator
    I need a web page for managing orders
    So that I can work with orders without calling the API directly

Scenario: The admin page is running
    When I open the Orders admin page
    Then I see the Orders heading

Scenario: Save a correction to an order
    Given I have opened an existing order on the admin page
    When I change an editable detail and save the order
    And I look up the same order again
    Then I see the corrected detail under the original order ID

Scenario: A failed lookup clears the previous selection
    Given I have opened an existing order on the admin page
    When I look up an order ID that does not exist
    Then I see an order-not-found message and no selected order

Scenario: Reject an incomplete item without creating an order
    Given I am on the order management page
    When I create an order with only a product ID
    Then I see an explanation that all item fields are needed
