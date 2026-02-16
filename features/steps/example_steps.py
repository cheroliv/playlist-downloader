from behave import given, when, then

@given('I have the number {number:d}')
def step_impl(context, number):
    if not hasattr(context, 'numbers'):
        context.numbers = []
    context.numbers.append(number)

@when('I add the two numbers')
def step_impl(context):
    context.result = sum(context.numbers)

@then('the result should be {expected_result:d}')
def step_impl(context, expected_result):
    assert context.result == expected_result, f"Expected {expected_result}, but got {context.result}"
