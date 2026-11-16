Feature: Cancel an eligible order from the admin page
    As an eCommerce administrator
    I want to cancel an eligible order
    So that fulfillment staff can stop processing it

Scenario: Cancel an order and retain its record
    Given I have opened an order that is eligible for cancellation
    When I cancel it on the admin page
    And I look it up again by the same ID
    Then the order is still present and its status shows it was cancelled

Scenario: Cancel the displayed order after editing the lookup input
    Given I have opened an order that is eligible for cancellation
    When I enter a different ID without looking it up
    And I cancel it on the admin page
    Then I see the cancellation confirmation
    When I look it up again by the same ID
    Then the order is still present and its status shows it was cancelled

Scenario: Pressing Cancel twice sends one cancellation
    Given I have opened an order that is eligible for cancellation
    When I press Cancel twice before the page responds
    Then I see the cancellation confirmation
    And only one cancellation request was sent with lookup locked

Scenario: A failed lookup clears the cancellation selection
    Given I have opened an order that is eligible for cancellation
    When I look up an order ID that does not exist
    Then I see an order-not-found message
    And the previous order details are no longer shown
    And cancellation is disabled and sends no request

Scenario Outline: Fulfilled orders cannot be cancelled on the page
    Given I have opened a "<status>" order for cancellation
    Then cancellation is disabled and sends no request

    Examples:
        | status    |
        | SHIPPED   |
        | DELIVERED |

Scenario: Recover from a cancellation failure
    Given I have opened an order that is eligible for cancellation
    And the next cancellation request fails
    When I cancel it on the admin page
    Then I see the cancellation error without stale order details
    When I look it up again by the same ID
    Then the order is still eligible for cancellation
    When I cancel it on the admin page
    Then I see the cancellation confirmation
    When I look it up again by the same ID
    Then the order is still present and its status shows it was cancelled

Scenario: The service rejects an order shipped after it was opened
    Given I have opened an order that is eligible for cancellation
    And the displayed order has shipped since it was opened
    When I cancel it on the admin page
    Then I see the service's cancellation conflict without stale details
    When I look it up again by the same ID
    Then the same order is still shipped
    And cancellation is disabled and sends no request
