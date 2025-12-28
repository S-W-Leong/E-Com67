"""
Product Search Analytics Tool

Provides product search capabilities for administrators using OpenSearch.
Enables searching products by name, description, category, and other attributes
to support inventory management and product analysis.

This tool is designed to be invoked by the Admin Insights Agent
to provide product discovery and search functionality.
"""

import os
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, validator

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Environment variables
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', '')
OPENSEARCH_INDEX = os.environ.get('OPENSEARCH_INDEX', 'products')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')

# Initialize OpenSearch client (lazy initialization)
opensearch_client = None


class ProductSearchToolInput(BaseModel):
    """Input schema for product search"""
    query: str = Field(..., description="Search query string (product name, description, tags)")
    category: Optional[str] = Field(None, description="Filter by product category")
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100)"
    )
    include_inactive: bool = Field(
        default=False,
        description="Include inactive products in results"
    )
    
    @validator('query')
    def validate_query(cls, query):
        """Ensure query is not empty"""
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        return query.strip()


class ProductResult(BaseModel):
    """Individual product search result"""
    product_id: str
    name: str
    description: str
    category: str
    price: float
    stock: int
    is_active: bool
    sku: Optional[str] = None
    brand: Optional[str] = None
    tags: List[str] = []
    relevance_score: Optional[float] = None


class ProductSearchToolOutput(BaseModel):
    """Output schema for product search"""
    products: List[ProductResult] = Field(
        description="List of matching products"
    )
    total_results: int = Field(
        description="Total number of matching products"
    )
    query: str = Field(
        description="Original search query"
    )
    filters_applied: Dict[str, Any] = Field(
        description="Filters that were applied to the search"
    )


def get_opensearch_client():
    """
    Get OpenSearch client with lazy initialization.
    
    Uses AWS IAM authentication with AWSV4SignerAuth.
    
    Returns:
        OpenSearch client instance
    """
    global opensearch_client
    
    if opensearch_client is None:
        if not OPENSEARCH_ENDPOINT:
            raise ValueError("OPENSEARCH_ENDPOINT environment variable not set")
        
        # Get AWS credentials for authentication
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, AWS_REGION, "es")
        
        # Remove https:// prefix if present
        endpoint = OPENSEARCH_ENDPOINT.replace("https://", "")
        
        opensearch_client = OpenSearch(
            hosts=[{"host": endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        
        logger.info("OpenSearch client initialized", extra={
            "endpoint": endpoint,
            "region": AWS_REGION
        })
    
    return opensearch_client


def convert_decimals_to_float(obj: Any) -> Any:
    """Convert DynamoDB Decimal objects to float for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(i) for i in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


@tracer.capture_method
def opensearch_query(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    include_inactive: bool = False
) -> Dict[str, Any]:
    """
    Execute OpenSearch query for products.
    
    Builds a multi-match query that searches across product name, description,
    and tags with fuzzy matching for typo tolerance.
    
    Args:
        query: Search query string
        category: Optional category filter
        limit: Maximum number of results
        include_inactive: Whether to include inactive products
    
    Returns:
        OpenSearch response with hits
    """
    logger.info("Executing OpenSearch query", extra={
        "query": query,
        "category": category,
        "limit": limit,
        "include_inactive": include_inactive
    })
    
    try:
        # Build OpenSearch query DSL
        search_body = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["name^3", "description^2", "tags", "brand", "sku"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",  # Handle typos
                                "operator": "or"
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},  # Sort by relevance
                {"createdAt": {"order": "desc"}}  # Then by creation date
            ]
        }
        
        # Add category filter if specified
        if category:
            search_body["query"]["bool"]["filter"].append({
                "term": {"category": category}
            })
        
        # Filter by active status unless including inactive
        if not include_inactive:
            search_body["query"]["bool"]["filter"].append({
                "term": {"isActive": True}
            })
        
        # Execute search
        client = get_opensearch_client()
        response = client.search(
            index=OPENSEARCH_INDEX,
            body=search_body
        )
        
        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)
        
        logger.info("OpenSearch query completed", extra={
            "total_hits": total_hits,
            "returned_hits": len(response.get("hits", {}).get("hits", []))
        })
        
        return response
        
    except Exception as e:
        logger.error("OpenSearch query failed", extra={
            "error": str(e),
            "query": query
        })
        raise


@tracer.capture_method
def filter_by_category(
    products: List[Dict[str, Any]],
    category: str
) -> List[Dict[str, Any]]:
    """
    Filter products by category (post-query filtering).
    
    This is a fallback filter in case OpenSearch filtering didn't work
    or for additional validation.
    
    Args:
        products: List of product documents
        category: Category to filter by
    
    Returns:
        Filtered list of products
    """
    logger.info("Filtering products by category", extra={
        "category": category,
        "input_count": len(products)
    })
    
    filtered = [
        product for product in products
        if product.get("category", "").lower() == category.lower()
    ]
    
    logger.info("Category filtering complete", extra={
        "output_count": len(filtered),
        "category": category
    })
    
    return filtered


@tracer.capture_method
def format_search_results(
    opensearch_response: Dict[str, Any],
    query: str,
    category: Optional[str] = None,
    include_inactive: bool = False
) -> ProductSearchToolOutput:
    """
    Format OpenSearch response into ProductSearchToolOutput.
    
    Extracts product data from OpenSearch hits and converts to
    structured ProductResult objects.
    
    Args:
        opensearch_response: Raw OpenSearch response
        query: Original search query
        category: Category filter applied
        include_inactive: Whether inactive products were included
    
    Returns:
        Formatted ProductSearchToolOutput
    """
    logger.info("Formatting search results", extra={
        "query": query
    })
    
    hits = opensearch_response.get("hits", {})
    total_results = hits.get("total", {}).get("value", 0)
    hit_list = hits.get("hits", [])
    
    products = []
    for hit in hit_list:
        source = hit.get("_source", {})
        score = hit.get("_score", 0)
        
        # Convert Decimals to floats
        source = convert_decimals_to_float(source)
        
        # Create ProductResult
        product = ProductResult(
            product_id=source.get("productId", ""),
            name=source.get("name", ""),
            description=source.get("description", ""),
            category=source.get("category", ""),
            price=float(source.get("price", 0)),
            stock=int(source.get("stock", 0)),
            is_active=source.get("isActive", False),
            sku=source.get("sku"),
            brand=source.get("brand"),
            tags=source.get("tags", []),
            relevance_score=float(score) if score else None
        )
        
        products.append(product)
    
    # Build filters applied dictionary
    filters_applied = {
        "category": category,
        "include_inactive": include_inactive
    }
    
    logger.info("Search results formatted", extra={
        "total_results": total_results,
        "products_returned": len(products)
    })
    
    return ProductSearchToolOutput(
        products=products,
        total_results=total_results,
        query=query,
        filters_applied=filters_applied
    )


@tracer.capture_method
def search_products(input_data: ProductSearchToolInput) -> ProductSearchToolOutput:
    """
    Main function to search products based on input parameters.
    
    Args:
        input_data: Validated input parameters
    
    Returns:
        ProductSearchToolOutput with search results
    """
    logger.info("Starting product search", extra={
        "query": input_data.query,
        "category": input_data.category,
        "limit": input_data.limit,
        "include_inactive": input_data.include_inactive
    })
    
    # Execute OpenSearch query
    opensearch_response = opensearch_query(
        query=input_data.query,
        category=input_data.category,
        limit=input_data.limit,
        include_inactive=input_data.include_inactive
    )
    
    # Format results
    result = format_search_results(
        opensearch_response=opensearch_response,
        query=input_data.query,
        category=input_data.category,
        include_inactive=input_data.include_inactive
    )
    
    logger.info("Product search complete", extra={
        "total_results": result.total_results,
        "products_returned": len(result.products)
    })
    
    return result


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for Product Search Analytics Tool.
    
    Expected event format:
    {
        "query": "wireless headphones",
        "category": "Electronics",
        "limit": 10,
        "include_inactive": false
    }
    """
    logger.info("Product Search Tool invoked", extra={"event": event})
    
    try:
        # Parse and validate input
        input_data = ProductSearchToolInput(**event)
        
        # Perform search
        result = search_products(input_data)
        
        # Return result
        return {
            "statusCode": 200,
            "body": json.dumps(result.dict(), default=str)
        }
        
    except ValueError as e:
        logger.error("Validation error", extra={"error": str(e)})
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "VALIDATION_ERROR",
                "message": str(e)
            })
        }
    
    except Exception as e:
        logger.exception("Unexpected error in Product Search Tool")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during product search"
            })
        }
