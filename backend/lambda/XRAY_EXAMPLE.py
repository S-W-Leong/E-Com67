"""
Example Lambda function demonstrating X-Ray SDK usage for custom tracing.

This shows how to use X-Ray SDK to create custom segments and subsegments
to trace specific operations in your Lambda functions.
"""

import json
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3

# Automatically instrument AWS SDK calls (DynamoDB, S3, SQS, etc.)
patch_all()

# Get environment variables
PRODUCTS_TABLE = os.environ.get('PRODUCTS_TABLE', 'e-com67-products')

# Initialize DynamoDB client (will be automatically traced)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(PRODUCTS_TABLE)


def handler(event, context):
    """
    Main Lambda handler with X-Ray tracing examples.
    
    With Active tracing enabled, Lambda automatically:
    - Creates a segment for the entire function execution
    - Captures AWS SDK calls (when using patch_all())
    - Adds metadata like cold start, memory, runtime, etc.
    """
    
    try:
        # Example 1: Automatic tracing of DynamoDB operations
        # This will automatically appear in X-Ray traces
        response = table.get_item(Key={'productId': 'example-id'})
        
        # Example 2: Create a custom subsegment for business logic
        with xray_recorder.capture('validate_product') as subsegment:
            # Add custom metadata to the subsegment
            subsegment.put_metadata('product_id', 'example-id')
            subsegment.put_annotation('category', 'electronics')
            
            # Your validation logic here
            is_valid = validate_product(response.get('Item', {}))
            
            # Add result to trace
            subsegment.put_metadata('validation_result', is_valid)
        
        # Example 3: Trace external API calls
        with xray_recorder.capture('call_external_api') as subsegment:
            subsegment.put_annotation('api_name', 'stripe')
            # result = call_stripe_api()
            pass
        
        # Example 4: Trace specific code blocks
        with xray_recorder.capture('calculate_price'):
            # Your price calculation logic
            total_price = calculate_total_price(response.get('Item', {}))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success',
                'product': response.get('Item', {})
            })
        }
        
    except Exception as e:
        # Exceptions are automatically captured in X-Ray traces
        xray_recorder.current_subsegment().put_annotation('error', str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def validate_product(product):
    """Business logic with custom annotations"""
    # Add custom annotations for filtering traces in X-Ray console
    xray_recorder.current_subsegment().put_annotation('has_stock', 
        product.get('stock', 0) > 0)
    
    return bool(product and product.get('stock', 0) > 0)


def calculate_total_price(product):
    """Price calculation example"""
    base_price = product.get('price', 0)
    tax_rate = 0.1
    
    # Add metadata (searchable in X-Ray)
    xray_recorder.current_subsegment().put_metadata('base_price', base_price)
    xray_recorder.current_subsegment().put_metadata('tax_rate', tax_rate)
    
    total = base_price * (1 + tax_rate)
    return total


"""
Key X-Ray Concepts:

1. SEGMENTS: Top-level trace units (automatically created by Lambda)
   - Represents the entire Lambda execution
   
2. SUBSEGMENTS: Nested trace units for specific operations
   - Use xray_recorder.capture('name') context manager
   - Can be nested for hierarchical tracing

3. ANNOTATIONS: Key-value pairs for FILTERING traces in X-Ray console
   - Limited to simple types (string, number, boolean)
   - Indexed for search
   - Use: subsegment.put_annotation(key, value)

4. METADATA: Additional data attached to traces (NOT indexed)
   - Can be complex objects
   - Use for debugging details
   - Use: subsegment.put_metadata(key, value)

5. AUTOMATIC INSTRUMENTATION:
   - patch_all() instruments boto3, requests, mysql, etc.
   - Captures AWS SDK calls automatically
   
X-Ray Console Features:
- Service Map: Visual representation of your architecture
- Traces: Individual request flows through your system
- Analytics: Query and filter traces using annotations
- Insights: Anomaly detection and performance analysis

Best Practices:
- Use annotations for filterable business metrics (user_id, category, etc.)
- Use metadata for detailed debugging info
- Create subsegments for expensive operations
- Don't create too many subsegments (impacts performance)
- Use meaningful names for subsegments
"""
