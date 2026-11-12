Feature: Filter orders by status on the admin page
    As an eCommerce administrator
    I want to filter orders by status
    So that I can find the orders that need attention

Scenario: Find pending orders
    Given there is a pending order and an order with a different status
    When I filter the list to pending orders on the admin page
    Then I see the pending order ID in the results
    And the other order ID is absent from the results

Scenario: Clear the status filter
    Given there is a pending order and an order with a different status
    When I filter the list to pending orders on the admin page
    And I clear the status filter
    Then I see both order IDs in the results
    And all statuses are selected

Scenario Outline: Find orders with each other supported status
    Given there is a pending order and a "<status>" order
    When I filter the list to "<status>" orders on the admin page
    Then I see the other order ID in the results
    And the pending order ID is absent from the results

    Examples:
        | status    |
        | SHIPPED   |
        | DELIVERED |
        | CANCELLED |

Scenario: Select all statuses after filtering
    Given there is a pending order and an order with a different status
    When I filter the list to pending orders on the admin page
    And I filter the list to all orders on the admin page
    Then I see both order IDs in the results

Scenario: No orders match the filter
    Given I am on the Orders admin page
    And the next order search returns no matches
    When I filter the list to pending orders on the admin page
    Then I see that no orders were found

Scenario: Recover from a failed search
    Given there is a pending order and an order with a different status
    And the next order search fails
    When I filter the list to pending orders on the admin page
    Then I see an order search error without stale results
    When I clear the status filter
    Then I see both order IDs in the results
