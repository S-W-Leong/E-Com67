"""
E-Com67 Platform Search Sync Function

This Lambda function is triggered by DynamoDB Streams to keep the OpenSearch
index synchronized with product data changes in real-time.

Handles:
- Product creation (INSERT events)
- Product updates (MODIFY events)
- Product deletion (REMOVE events)
"""

import json
import os
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()

# Environment variables
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_INDEX = "products"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize OpenSearch client
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, AWS_REGION, "es")  # Changed from "aoss" to "es" for regular OpenSearch Service

opensearch_client = OpenSearch(
    hosts=[{"host": OPENSEARCH_ENDPOINT.replace("https://", ""), "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30
)


@tracer.capture_method
def create_index_if_not_exists():
    """
    Create the products index with proper mappings if it doesn't exist.
    
    This defines the schema for product search including:
    - Full-text search fields (name, description)
    - Keyword fields for exact matching (category, tags)
    - Numeric fields (price)
    - Completion suggester for autocomplete
    """
    
    if opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
        logger.info(f"Index {OPENSEARCH_INDEX} already exists")
        return
    
    # Define index mapping based on design document
    index_mapping = {
        "mappings": {
            "properties": {
                "productId": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "description": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "category": {"type": "keyword"},
                "price": {"type": "float"},
                "stock": {"type": "integer"},
                "tags": {"type": "keyword"},
                "isActive": {"type": "boolean"},
                "createdAt": {"type": "date", "format": "epoch_second"},
                "updatedAt": {"type": "date", "format": "epoch_second"},
                "suggest": {
                    "type": "completion",
                    "analyzer": "simple"
                }
            }
        },
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0  # Serverless manages replication
            }
        }
    }
    
    try:
        opensearch_client.indices.create(index=OPENSEARCH_INDEX, body=index_mapping)
        logger.info(f"Created index {OPENSEARCH_INDEX} with mappings")
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        raise


@tracer.capture_method
def transform_product_for_search(product_data):
    """
    Transform DynamoDB product data into OpenSearch document format.
    
    Args:
        product_data: Product data from DynamoDB
        
    Returns:
        dict: Transformed document ready for OpenSearch indexing
    """
    
    # Extract product fields
    doc = {
        "productId": product_data.get("productId", ""),
        "name": product_data.get("name", ""),
        "description": product_data.get("description", ""),
        "category": product_data.get("category", ""),
        "price": float(product_data.get("price", 0)),
        "stock": int(product_data.get("stock", 0)),
        "tags": product_data.get("tags", []),
        "isActive": product_data.get("isActive", True),
        "createdAt": int(product_data.get("createdAt", 0)),
        "updatedAt": int(product_data.get("updatedAt", 0))
    }
    
    # Add suggestion field for autocomplete (using product name)
    doc["suggest"] = {
        "input": [doc["name"]],
        "weight": int(doc["price"])  # Higher priced items get slight boost
    }
    
    return doc


@tracer.capture_method
def index_product(product_data):
    """
    Index a product document in OpenSearch.
    
    Args:
        product_data: Product data from DynamoDB
    """
    
    product_id = product_data.get("productId")
    if not product_id:
        logger.warning("Product data missing productId, skipping indexing")
        return
    
    try:
        doc = transform_product_for_search(product_data)
        
        response = opensearch_client.index(
            index=OPENSEARCH_INDEX,
            id=product_id,
            body=doc,
            refresh=True  # Make immediately searchable
        )
        
        logger.info(f"Indexed product {product_id}: {response['result']}")
        
    except Exception as e:
        logger.error(f"Error indexing product {product_id}: {str(e)}")
        raise


@tracer.capture_method
def delete_product(product_id):
    """
    Delete a product document from OpenSearch.
    
    Args:
        product_id: ID of the product to delete
    """
    
    try:
        response = opensearch_client.delete(
            index=OPENSEARCH_INDEX,
            id=product_id,
            refresh=True
        )
        
        logger.info(f"Deleted product {product_id}: {response['result']}")
        
    except Exception as e:
        if "not_found" in str(e).lower():
            logger.warning(f"Product {product_id} not found in search index")
        else:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise


@tracer.capture_method
def process_stream_record(record):
    """
    Process a single DynamoDB Stream record.
    
    Args:
        record: DynamoDB Stream record containing event data
    """
    
    event_name = record.get("eventName")
    logger.info(f"Processing {event_name} event")
    
    if event_name == "INSERT" or event_name == "MODIFY":
        # Index new or updated product
        new_image = record.get("dynamodb", {}).get("NewImage", {})
        if new_image:
            # Convert DynamoDB format to regular dict
            product_data = {
                key: list(value.values())[0] for key, value in new_image.items()
            }
            index_product(product_data)
    
    elif event_name == "REMOVE":
        # Delete product from search index
        old_image = record.get("dynamodb", {}).get("OldImage", {})
        if old_image:
            product_id = old_image.get("productId", {}).get("S", "")
            if product_id:
                delete_product(product_id)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Lambda handler for DynamoDB Stream events.
    
    This function is triggered whenever products are created, updated, or deleted
    in DynamoDB, and keeps the OpenSearch index synchronized.
    
    Args:
        event: DynamoDB Stream event containing records
        context: Lambda context object
        
    Returns:
        dict: Response with processing results
    """
    
    logger.info(f"Received {len(event.get('Records', []))} stream records")
    
    # Ensure index exists
    create_index_if_not_exists()
    
    # Process each record
    processed = 0
    failed = 0
    
    for record in event.get("Records", []):
        try:
            process_stream_record(record)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process record: {str(e)}")
            failed += 1
    
    result = {
        "processed": processed,
        "failed": failed,
        "total": len(event.get("Records", []))
    }
    
    logger.info(f"Processing complete: {result}")
    
    # Return success even if some records failed (they'll be retried)
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
