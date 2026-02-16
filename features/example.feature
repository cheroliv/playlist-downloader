Feature: Basic arithmetic operations

  Scenario: Adding two numbers
    Given I have the number 5
    And I have the number 3
    When I add the two numbers
    Then the result should be 8
