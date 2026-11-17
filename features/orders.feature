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

Scenario: Pressing Create twice sends one order
    Given I am on the Orders admin page
    When I fill in the details for a new order
    And I press Create twice before the page responds
    Then I see a creation confirmation and the new order ID
    And only one create request was sent

Scenario: An error after a successful creation hides the earlier order ID
    Given I have created an order on the admin page
    When I submit a new order without a customer ID
    Then I see a message explaining what is wrong
    And no order ID is shown

Scenario: Retrieve the order I entered
    Given I have created an order on the admin page
    When I look up its order ID
    Then I see that same ID and the order details I entered

Scenario: Look up an order that does not exist
    Given I have looked up an order on the admin page
    When I look up an order ID that does not exist
    Then I see an order-not-found message
    And the previous order details are no longer shown

Scenario: Pressing Look up twice sends one lookup
    Given I have created an order on the admin page
    When I press Look up twice for its order ID
    Then I see that same ID and the order details I entered
    And only one lookup request was sent

Scenario: Save a correction to an order
    Given I have opened an existing order on the admin page
    When I change an editable detail and save the order
    And I look up the same order again
    Then I see the corrected detail under the original order ID

Scenario: A failed lookup clears the order available for update
    Given I have looked up an order on the admin page
    When I look up an order ID that does not exist
    Then I see an order-not-found message
    And the update form is hidden
