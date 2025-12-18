#!/usr/bin/env python3
"""
Integration tests for E-Com67 Step Functions checkout workflow.

This script tests the complete checkout flow including:
1. Cart validation
2. Payment processing
3. Order queue submission
4. End-to-end success/failure scenarios
"""

import json
import time
import boto3
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Configuration
STATE_MACHINE_NAME = "e-com67-checkout-workflow"
CART_TABLE_NAME = "e-com67-cart"
PRODUCTS_TABLE_NAME = "e-com67-products"
ORDERS_TABLE_NAME = "e-com67-orders"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(message: str):
    """Print a formatted header"""
    print(f"\n{Colors.YELLOW}{'=' * 60}{Colors.NC}")
    print(f"{Colors.YELLOW}{message}{Colors.NC}")
    print(f"{Colors.YELLOW}{'=' * 60}{Colors.NC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")


def get_state_machine_arn() -> str:
    """Get the ARN of the checkout state machine"""
    response = stepfunctions.list_state_machines()
    for sm in response['stateMachines']:
        if sm['name'] == STATE_MACHINE_NAME:
            return sm['stateMachineArn']
    raise Exception(f"State machine '{STATE_MACHINE_NAME}' not found")


def create_test_product(product_id: str, name: str, price: float, stock: int = 100) -> Dict:
    """Create a test product in DynamoDB"""
    products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)

    product = {
        'productId': product_id,
        'name': name,
        'description': f'Test product: {name}',
        'price': Decimal(str(price)),  # Convert float to Decimal for DynamoDB
        'category': 'Test',
        'stock': stock,
        'imageUrl': 'https://example.com/image.jpg',
        'tags': ['test'],
        'isActive': True,
        'createdAt': int(time.time()),
        'updatedAt': int(time.time())
    }

    products_table.put_item(Item=product)
    print_success(f"Created test product: {product_id} - {name} (${price})")

    # Return with float price for convenience in test code
    return {**product, 'price': float(product['price'])}


def create_test_cart(user_id: str, products: list) -> None:
    """Create test cart items in DynamoDB"""
    cart_table = dynamodb.Table(CART_TABLE_NAME)

    for product in products:
        cart_item = {
            'userId': user_id,
            'productId': product['productId'],
            'name': product['name'],
            'price': Decimal(str(product['price'])),  # Convert float to Decimal
            'quantity': product.get('quantity', 1),
            'imageUrl': product.get('imageUrl', ''),
            'addedAt': int(time.time()),
            'updatedAt': int(time.time())
        }
        cart_table.put_item(Item=cart_item)

    print_success(f"Created cart with {len(products)} items for user {user_id}")


def start_execution(state_machine_arn: str, input_data: Dict[str, Any], name_suffix: str) -> str:
    """Start a Step Functions execution"""
    execution_name = f"test-{name_suffix}-{int(time.time())}"

    response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps(input_data)
    )

    return response['executionArn']


def wait_for_execution(execution_arn: str, timeout: int = 30) -> Dict[str, Any]:
    """Wait for execution to complete and return the result"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = stepfunctions.describe_execution(executionArn=execution_arn)
        status = response['status']

        if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
            return response

        time.sleep(2)

    raise TimeoutError(f"Execution did not complete within {timeout} seconds")


def get_execution_output(execution_arn: str) -> Optional[Dict]:
    """Get the output of a completed execution"""
    response = stepfunctions.describe_execution(executionArn=execution_arn)

    if 'output' in response and response['output']:
        return json.loads(response['output'])

    return None


def test_valid_checkout():
    """Test Case 1: Valid checkout with products in stock"""
    print_header("Test 1: Valid Checkout Flow")

    # Setup test data
    user_id = f"test-user-{uuid.uuid4()}"
    order_id = f"order-{uuid.uuid4()}"

    # Create test products
    product1 = create_test_product(f"prod-{uuid.uuid4()}", "Test Widget", 29.99, stock=50)
    product2 = create_test_product(f"prod-{uuid.uuid4()}", "Test Gadget", 49.99, stock=30)

    # Create cart
    cart_products = [
        {**product1, 'quantity': 2},
        {**product2, 'quantity': 1}
    ]
    create_test_cart(user_id, cart_products)

    # Prepare execution input
    subtotal = (29.99 * 2) + (49.99 * 1)
    tax_amount = subtotal * 0.08
    total_amount = subtotal + tax_amount

    execution_input = {
        'userId': user_id,
        'orderId': order_id,
        'items': [
            {
                'productId': product1['productId'],
                'name': product1['name'],
                'price': product1['price'],
                'quantity': 2,
                'itemTotal': 29.99 * 2
            },
            {
                'productId': product2['productId'],
                'name': product2['name'],
                'price': product2['price'],
                'quantity': 1,
                'itemTotal': 49.99
            }
        ],
        'subtotal': subtotal,
        'taxAmount': tax_amount,
        'totalAmount': total_amount,
        'currency': 'usd',
        'shippingAddress': {
            'street': '123 Test St',
            'city': 'Seattle',
            'state': 'WA',
            'zip': '98101',
            'country': 'USA'
        }
    }

    print_info(f"Execution input:\n{json.dumps(execution_input, indent=2)}")

    # Start execution
    state_machine_arn = get_state_machine_arn()
    execution_arn = start_execution(state_machine_arn, execution_input, "valid-checkout")
    print_info(f"Execution started: {execution_arn}")

    # Wait for completion
    print_info("Waiting for execution to complete...")
    result = wait_for_execution(execution_arn)

    # Check result
    if result['status'] == 'SUCCEEDED':
        print_success(f"Execution SUCCEEDED")
        output = get_execution_output(execution_arn)
        if output:
            print_info(f"Output:\n{json.dumps(output, indent=2)}")
        return True
    else:
        print_error(f"Execution {result['status']}")
        if 'error' in result:
            print_error(f"Error: {result.get('error')}")
        return False


def test_empty_cart():
    """Test Case 2: Empty cart should fail validation"""
    print_header("Test 2: Empty Cart (Should Fail)")

    user_id = f"test-user-{uuid.uuid4()}"
    order_id = f"order-{uuid.uuid4()}"

    execution_input = {
        'userId': user_id,
        'orderId': order_id,
        'items': [],
        'subtotal': 0,
        'taxAmount': 0,
        'totalAmount': 0,
        'currency': 'usd'
    }

    print_info(f"Execution input:\n{json.dumps(execution_input, indent=2)}")

    state_machine_arn = get_state_machine_arn()
    execution_arn = start_execution(state_machine_arn, execution_input, "empty-cart")
    print_info(f"Execution started: {execution_arn}")

    print_info("Waiting for execution to complete...")
    result = wait_for_execution(execution_arn)

    # This should FAIL
    if result['status'] == 'FAILED':
        print_success("Execution FAILED as expected (empty cart)")
        return True
    else:
        print_error(f"Execution {result['status']} - Expected FAILED")
        return False


def test_insufficient_stock():
    """Test Case 3: Insufficient stock should fail validation"""
    print_header("Test 3: Insufficient Stock (Should Fail)")

    user_id = f"test-user-{uuid.uuid4()}"
    order_id = f"order-{uuid.uuid4()}"

    # Create product with low stock
    product = create_test_product(f"prod-{uuid.uuid4()}", "Low Stock Item", 19.99, stock=2)

    # Try to order more than available
    cart_products = [{**product, 'quantity': 5}]
    create_test_cart(user_id, cart_products)

    execution_input = {
        'userId': user_id,
        'orderId': order_id,
        'items': [
            {
                'productId': product['productId'],
                'name': product['name'],
                'price': product['price'],
                'quantity': 5,
                'itemTotal': 19.99 * 5
            }
        ],
        'subtotal': 99.95,
        'taxAmount': 7.996,
        'totalAmount': 107.946,
        'currency': 'usd'
    }

    print_info(f"Execution input:\n{json.dumps(execution_input, indent=2)}")

    state_machine_arn = get_state_machine_arn()
    execution_arn = start_execution(state_machine_arn, execution_input, "insufficient-stock")
    print_info(f"Execution started: {execution_arn}")

    print_info("Waiting for execution to complete...")
    result = wait_for_execution(execution_arn)

    # This should FAIL
    if result['status'] == 'FAILED':
        print_success("Execution FAILED as expected (insufficient stock)")
        return True
    else:
        print_error(f"Execution {result['status']} - Expected FAILED")
        return False


def main():
    """Run all integration tests"""
    print_header("E-Com67 Step Functions Integration Tests")

    results = {
        'Test 1 - Valid Checkout': False,
        'Test 2 - Empty Cart': False,
        'Test 3 - Insufficient Stock': False
    }

    try:
        # Verify state machine exists
        state_machine_arn = get_state_machine_arn()
        print_success(f"Found state machine: {STATE_MACHINE_NAME}")
        print_info(f"ARN: {state_machine_arn}\n")

        # Run tests
        results['Test 1 - Valid Checkout'] = test_valid_checkout()
        results['Test 2 - Empty Cart'] = test_empty_cart()
        results['Test 3 - Insufficient Stock'] = test_insufficient_stock()

    except Exception as e:
        print_error(f"Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Print summary
    print_header("Test Results Summary")

    all_passed = True
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
            all_passed = False

    print()
    if all_passed:
        print_success("All tests passed! 🎉")
    else:
        print_error("Some tests failed. Check the output above for details.")

    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
