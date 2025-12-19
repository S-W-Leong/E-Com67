"""
E-Com67 Platform Search Function

This Lambda function provides full-text search capabilities using OpenSearch.
It handles product search queries with features like:
- Full-text search across name and description
- Category filtering
- Price range filtering
- Search suggestions and autocomplete
- Result highlighting
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
auth = AWSV4SignerAuth(credentials, AWS_REGION, "aoss")

opensearch_client = OpenSearch(
    hosts=[{"host": OPENSEARCH_ENDPOINT.replace("https://", ""), "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30
)


@tracer.capture_method
def build_search_query(query_params):
    """
    Build OpenSearch query based on request parameters.
    
    Args:
        query_params: Dictionary of query parameters
        
    Returns:
        dict: OpenSearch query DSL
    """
    
    # Extract parameters
    search_term = query_params.get("q", "").strip()
    category = query_params.get("category", "")
    min_price = query_params.get("min_price")
    max_price = query_params.get("max_price")
    page = int(query_params.get("page", 1))
    size = int(query_params.get("size", 20))
    
    # Calculate pagination
    from_offset = (page - 1) * size
    
    # Build query
    query = {
        "from": from_offset,
        "size": size,
        "query": {
            "bool": {
                "must": [],
                "filter": []
            }
        },
        "highlight": {
            "fields": {
                "name": {},
                "description": {}
            }
        },
        "sort": []
    }
    
    # Add text search if provided
    if search_term:
        query["query"]["bool"]["must"].append({
            "multi_match": {
                "query": search_term,
                "fields": ["name^2", "description"],  # Boost name field
                "type": "best_fields",
                "fuzziness": "AUTO"  # Handle typos
            }
        })
        
        # Sort by relevance score when searching
        query["sort"].append({"_score": {"order": "desc"}})
    else:
        # Default sort by creation date when browsing
        query["sort"].append({"createdAt": {"order": "desc"}})
    
    # Add category filter
    if category:
        query["query"]["bool"]["filter"].append({
            "term": {"category": category}
        })
    
    # Add price range filter
    if min_price is not None or max_price is not None:
        price_range = {}
        if min_price is not None:
            price_range["gte"] = float(min_price)
        if max_price is not None:
            price_range["lte"] = float(max_price)
        
        query["query"]["bool"]["filter"].append({
            "range": {"price": price_range}
        })
    
    # Only show active products
    query["query"]["bool"]["filter"].append({
        "term": {"isActive": True}
    })
    
    # Add aggregations for faceted search
    query["aggs"] = {
        "categories": {
            "terms": {"field": "category", "size": 10}
        },
        "price_ranges": {
            "range": {
                "field": "price",
                "ranges": [
                    {"to": 25, "key": "Under $25"},
                    {"from": 25, "to": 50, "key": "$25 - $50"},
                    {"from": 50, "to": 100, "key": "$50 - $100"},
                    {"from": 100, "to": 200, "key": "$100 - $200"},
                    {"from": 200, "key": "Over $200"}
                ]
            }
        }
    }
    
    return query


@tracer.capture_method
def format_search_results(response):
    """
    Format OpenSearch response for API consumption.
    
    Args:
        response: Raw OpenSearch response
        
    Returns:
        dict: Formatted search results
    """
    
    hits = response.get("hits", {})
    total = hits.get("total", {}).get("value", 0)
    
    # Format products
    products = []
    for hit in hits.get("hits", []):
        product = hit["_source"]
        
        # Add highlighting if available
        if "highlight" in hit:
            product["_highlight"] = hit["highlight"]
        
        # Add relevance score
        product["_score"] = hit.get("_score", 0)
        
        products.append(product)
    
    # Format aggregations for faceted search
    aggregations = response.get("aggregations", {})
    facets = {}
    
    if "categories" in aggregations:
        facets["categories"] = [
            {
                "value": bucket["key"],
                "count": bucket["doc_count"]
            }
            for bucket in aggregations["categories"]["buckets"]
        ]
    
    if "price_ranges" in aggregations:
        facets["price_ranges"] = [
            {
                "label": bucket["key"],
                "count": bucket["doc_count"],
                "from": bucket.get("from"),
                "to": bucket.get("to")
            }
            for bucket in aggregations["price_ranges"]["buckets"]
            if bucket["doc_count"] > 0
        ]
    
    return {
        "products": products,
        "total": total,
        "facets": facets
    }


@tracer.capture_method
def get_search_suggestions(query_term, size=5):
    """
    Get search suggestions using completion suggester.
    
    Args:
        query_term: Partial search term
        size: Number of suggestions to return
        
    Returns:
        list: Search suggestions
    """
    
    if not query_term or len(query_term) < 2:
        return []
    
    try:
        suggest_query = {
            "suggest": {
                "product_suggest": {
                    "prefix": query_term,
                    "completion": {
                        "field": "suggest",
                        "size": size
                    }
                }
            }
        }
        
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body=suggest_query
        )
        
        suggestions = []
        for option in response.get("suggest", {}).get("product_suggest", [{}])[0].get("options", []):
            suggestions.append({
                "text": option["text"],
                "score": option["_score"]
            })
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return []


@tracer.capture_method
def handle_search_request(event):
    """
    Handle search API request.
    
    Args:
        event: API Gateway event
        
    Returns:
        dict: API response
    """
    
    # Extract query parameters
    query_params = event.get("queryStringParameters") or {}
    
    # Handle suggestions endpoint
    if event.get("path", "").endswith("/suggest"):
        query_term = query_params.get("q", "")
        suggestions = get_search_suggestions(query_term)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "suggestions": suggestions
            })
        }
    
    # Handle main search
    try:
        # Build and execute search query
        search_query = build_search_query(query_params)
        logger.info(f"Executing search query: {json.dumps(search_query)}")
        
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body=search_query
        )
        
        # Format results
        results = format_search_results(response)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(results)
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Search service temporarily unavailable",
                "message": str(e)
            })
        }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Lambda handler for search API requests.
    
    Supports:
    - GET /search?q=term&category=cat&min_price=10&max_price=100
    - GET /search/suggest?q=partial_term
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        dict: API Gateway response
    """
    
    logger.info(f"Search request: {event.get('httpMethod')} {event.get('path')}")
    
    # Only handle GET requests
    if event.get("httpMethod") != "GET":
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Method not allowed"})
        }
    
    return handle_search_request(event)