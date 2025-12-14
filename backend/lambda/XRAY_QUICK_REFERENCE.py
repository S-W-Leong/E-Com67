"""
Quick Reference: X-Ray SDK Usage in Lambda Functions

Copy-paste these snippets into your Lambda handlers for instant X-Ray tracing.
"""

# ============================================================================
# BASIC SETUP (Add to top of every Lambda handler)
# ============================================================================

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3

# Automatically instrument AWS SDK - MUST BE BEFORE boto3 imports
patch_all()

# Now initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sqs = boto3.client('sqs')


# ============================================================================
# PATTERN 1: Trace DynamoDB Operations
# ============================================================================

def get_product(product_id):
    """DynamoDB operations are auto-traced when patch_all() is used"""
    table = dynamodb.Table('e-com67-products')
    
    # This will automatically appear in X-Ray traces
    response = table.get_item(Key={'productId': product_id})
    
    return response.get('Item')


# ============================================================================
# PATTERN 2: Trace Business Logic with Custom Subsegments
# ============================================================================

def validate_cart(cart_items, user_id):
    """Add custom subsegments for business logic"""
    
    with xray_recorder.capture('validate_cart') as subsegment:
        # Annotations: for FILTERING in X-Ray console
        subsegment.put_annotation('user_id', user_id)
        subsegment.put_annotation('item_count', len(cart_items))
        
        # Metadata: for DEBUGGING (not indexed)
        subsegment.put_metadata('cart_items', cart_items)
        
        # Your validation logic
        total_price = sum(item['price'] for item in cart_items)
        is_valid = total_price > 0
        
        subsegment.put_annotation('is_valid', is_valid)
        subsegment.put_metadata('total_price', total_price)
        
        return is_valid


# ============================================================================
# PATTERN 3: Trace External API Calls (Stripe, etc.)
# ============================================================================

def process_payment(amount, token, user_id):
    """Trace external API calls"""
    
    with xray_recorder.capture('stripe_payment') as subsegment:
        # Add searchable annotations
        subsegment.put_annotation('user_id', user_id)
        subsegment.put_annotation('amount', amount)
        subsegment.put_annotation('currency', 'USD')
        
        try:
            # Your Stripe/payment API call
            # response = stripe.Charge.create(...)
            
            subsegment.put_annotation('payment_status', 'success')
            return {'status': 'success'}
            
        except Exception as e:
            subsegment.put_annotation('payment_status', 'failed')
            subsegment.put_metadata('error', str(e))
            raise


# ============================================================================
# PATTERN 4: Trace Multiple Steps in Order Processing
# ============================================================================

def process_order(order_data):
    """Trace complex workflows with nested subsegments"""
    
    # Step 1: Validate order
    with xray_recorder.capture('validate_order') as subsegment:
        subsegment.put_annotation('order_id', order_data['orderId'])
        is_valid = validate_order_data(order_data)
        subsegment.put_annotation('validation_result', is_valid)
    
    # Step 2: Reserve inventory
    with xray_recorder.capture('reserve_inventory'):
        for item in order_data['items']:
            # Each DynamoDB update is auto-traced
            reserve_product(item['productId'], item['quantity'])
    
    # Step 3: Process payment
    with xray_recorder.capture('payment_processing'):
        payment_result = process_payment(
            order_data['total'],
            order_data['paymentToken'],
            order_data['userId']
        )
    
    # Step 4: Send confirmation
    with xray_recorder.capture('send_notification') as subsegment:
        subsegment.put_annotation('notification_type', 'email')
        send_order_confirmation(order_data)
    
    return {'orderId': order_data['orderId'], 'status': 'processed'}


# ============================================================================
# PATTERN 5: Error Handling with X-Ray
# ============================================================================

def handler(event, context):
    """Main handler with proper error tracing"""
    
    try:
        # Your main logic
        result = process_request(event)
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except ValueError as e:
        # Annotate with error type for filtering
        xray_recorder.current_subsegment().put_annotation('error_type', 'ValidationError')
        xray_recorder.current_subsegment().put_metadata('error_details', str(e))
        
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid input'})
        }
        
    except Exception as e:
        # Generic error handling
        xray_recorder.current_subsegment().put_annotation('error_type', 'InternalError')
        xray_recorder.current_subsegment().put_metadata('error_details', str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


# ============================================================================
# PATTERN 6: Conditional Tracing (Debug Mode)
# ============================================================================

import os

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'

def expensive_calculation(data):
    """Only create subsegments in debug mode"""
    
    if DEBUG_MODE:
        with xray_recorder.capture('expensive_calculation') as subsegment:
            subsegment.put_metadata('input_size', len(data))
            result = do_calculation(data)
            subsegment.put_metadata('result', result)
            return result
    else:
        # No tracing overhead in production
        return do_calculation(data)


# ============================================================================
# PATTERN 7: Async Operations (SQS, SNS)
# ============================================================================

def send_to_queue(message, queue_url):
    """Trace SQS message sending"""
    
    with xray_recorder.capture('send_sqs_message') as subsegment:
        subsegment.put_annotation('queue_name', queue_url.split('/')[-1])
        subsegment.put_annotation('message_type', message.get('type'))
        
        # SQS send is auto-traced with patch_all()
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        subsegment.put_metadata('message_id', response['MessageId'])
        return response


# ============================================================================
# PATTERN 8: Database Batch Operations
# ============================================================================

def batch_get_products(product_ids):
    """Trace batch operations"""
    
    with xray_recorder.capture('batch_get_products') as subsegment:
        subsegment.put_annotation('batch_size', len(product_ids))
        
        # DynamoDB batch_get is auto-traced
        response = dynamodb.batch_get_item(
            RequestItems={
                'e-com67-products': {
                    'Keys': [{'productId': pid} for pid in product_ids]
                }
            }
        )
        
        items = response['Responses']['e-com67-products']
        subsegment.put_metadata('items_retrieved', len(items))
        
        return items


# ============================================================================
# USEFUL X-RAY CONSOLE QUERIES
# ============================================================================

"""
# Find all failed payments:
annotation.payment_status = "failed"

# Find slow requests (> 1 second):
responsetime > 1

# Find requests from specific user:
annotation.user_id = "user123"

# Find errors in cart validation:
annotation.error_type = "ValidationError" AND service("CartFunction")

# Find high-value orders:
annotation.amount > 100

# Combine filters:
annotation.user_id = "user123" AND annotation.payment_status = "success"
"""


# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================

"""
✅ 1. Add to top of Lambda handler:
   from aws_xray_sdk.core import xray_recorder, patch_all
   patch_all()

✅ 2. Wrap business logic in subsegments:
   with xray_recorder.capture('operation_name'):
       ...

✅ 3. Add meaningful annotations (for filtering):
   subsegment.put_annotation('user_id', user_id)

✅ 4. Add metadata for debugging:
   subsegment.put_metadata('details', complex_object)

✅ 5. Test locally (if possible) before deploying

✅ 6. Deploy: cdk deploy

✅ 7. Generate traffic and check X-Ray console
"""
