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
