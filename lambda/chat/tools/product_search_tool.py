"""
Product Search Tool for Strands AI Agent

This tool enables the Strands agent to search for products using the E-Com67
platform's OpenSearch infrastructure and provide intelligent recommendations.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from botocore.exceptions import ClientError

from strands import tool
from ..models import ProductSearchResponse, ProductInfo, ProductRecommendation

# Initialize logger
logger = logging.getLogger(__name__)

# Environment variables
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_INDEX = "products"
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
PRODUCTS_TABLE_NAME = os.environ.get("PRODUCTS_TABLE_NAME", "")

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
products_table = None

# Initialize OpenSearch client
opensearch_client = None


def get_opensearch_client():
    """Get OpenSearch client with lazy initialization"""
    global opensearch_client
    if opensearch_client is None:
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, AWS_REGION, "es")
        
        opensearch_client = OpenSearch(
            hosts=[{"host": OPENSEARCH_ENDPOINT.replace("https://", ""), "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
    return opensearch_client


def get_products_table():
    """Get products table with lazy initialization"""
    global products_table
    if products_table is None:
        products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)
    return products_table


def convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj


class ProductSearchTool:
    """Product search and recommendation tool for Strands agent"""
    
    def __init__(self, user_context: Optional[Dict[str, Any]] = None):
        """Initialize the product search tool with user context"""
        self.user_context = user_context or {}
        self.user_id = self.user_context.get('user_id')
        
    def build_search_query(self, query: str, category: Optional[str] = None, 
                          price_range: Optional[Dict[str, float]] = None, 
                          limit: int = 10) -> Dict[str, Any]:
        """
        Build OpenSearch query based on search parameters.
        
        Args:
            query: Search query string
            category: Optional category filter
            price_range: Optional price range with 'min' and 'max' keys
            limit: Maximum number of results to return
            
        Returns:
            OpenSearch query DSL
        """
        search_query = {
            "size": limit,
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
        if query.strip():
            search_query["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "description", "tags"],  # Boost name field
                    "type": "best_fields",
                    "fuzziness": "AUTO"  # Handle typos
                }
            })
            
            # Sort by relevance score when searching
            search_query["sort"].append({"_score": {"order": "desc"}})
        else:
            # Default sort by creation date when browsing
            search_query["sort"].append({"createdAt": {"order": "desc"}})
        
        # Add category filter
        if category:
            search_query["query"]["bool"]["filter"].append({
                "term": {"category": category}
            })
        
        # Add price range filter
        if price_range:
            price_filter = {}
            if price_range.get('min') is not None:
                price_filter["gte"] = float(price_range['min'])
            if price_range.get('max') is not None:
                price_filter["lte"] = float(price_range['max'])
            
            if price_filter:
                search_query["query"]["bool"]["filter"].append({
                    "range": {"price": price_filter}
                })
        
        # Only show active products
        search_query["query"]["bool"]["filter"].append({
            "term": {"isActive": True}
        })
        
        return search_query
    
    def format_product_info(self, product_data: Dict[str, Any]) -> ProductInfo:
        """
        Format product data into ProductInfo model.
        
        Args:
            product_data: Raw product data from OpenSearch or DynamoDB
            
        Returns:
            ProductInfo model instance
        """
        # Convert Decimal objects to float
        product_data = convert_decimals_to_float(product_data)
        
        return ProductInfo(
            product_id=product_data.get('productId', ''),
            name=product_data.get('name', ''),
            description=product_data.get('description', ''),
            price=float(product_data.get('price', 0)),
            currency=product_data.get('currency', 'USD'),
            category=product_data.get('category', ''),
            stock=int(product_data.get('stock', 0)),
            image_url=product_data.get('imageUrl'),
            rating=product_data.get('rating'),
            tags=product_data.get('tags', []),
            is_available=product_data.get('isActive', False) and product_data.get('stock', 0) > 0,
            specifications=product_data.get('specifications', {}),
            brand=product_data.get('brand'),
            sku=product_data.get('sku')
        )
    
    def generate_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Generate search suggestions for no-results scenarios.
        
        Args:
            query: Original search query
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        suggestions = []
        
        try:
            # Try to get suggestions from OpenSearch completion suggester
            suggest_query = {
                "suggest": {
                    "product_suggest": {
                        "prefix": query,
                        "completion": {
                            "field": "suggest",
                            "size": limit
                        }
                    }
                }
            }
            
            response = get_opensearch_client().search(
                index=OPENSEARCH_INDEX,
                body=suggest_query
            )
            
            for option in response.get("suggest", {}).get("product_suggest", [{}])[0].get("options", []):
                suggestions.append(option["text"])
                
        except Exception as e:
            logger.warning(f"Failed to get OpenSearch suggestions: {str(e)}")
        
        # If no suggestions from OpenSearch, provide fallback suggestions
        if not suggestions:
            # Simple fallback suggestions based on common categories
            fallback_suggestions = [
                "electronics",
                "clothing",
                "books",
                "home & garden",
                "sports & outdoors"
            ]
            
            # Filter suggestions that might be related to the query
            query_lower = query.lower()
            for suggestion in fallback_suggestions:
                if any(word in suggestion for word in query_lower.split()):
                    suggestions.append(suggestion)
            
            # If still no matches, return general suggestions
            if not suggestions:
                suggestions = fallback_suggestions[:limit]
        
        return suggestions[:limit]
    
    def calculate_relevance_score(self, product: Dict[str, Any], query: str, 
                                 category_match: bool, price_match: bool) -> float:
        """
        Calculate relevance score for product recommendations.
        
        Args:
            product: Product data
            query: Search query
            category_match: Whether category matches
            price_match: Whether price is in range
            
        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0
        
        # Base score from search relevance (if available)
        if '_score' in product:
            # Normalize OpenSearch score (typically 0-10) to 0-0.5
            score += min(product['_score'] / 20.0, 0.5)
        
        # Category match bonus
        if category_match:
            score += 0.2
        
        # Price match bonus
        if price_match:
            score += 0.1
        
        # Stock availability bonus
        if product.get('stock', 0) > 0:
            score += 0.1
        
        # Rating bonus (if available)
        rating = product.get('rating')
        if rating:
            score += (rating / 5.0) * 0.1  # Up to 0.1 bonus for 5-star rating
        
        return min(score, 1.0)  # Cap at 1.0
    
    def generate_recommendation_reasoning(self, product: Dict[str, Any], query: str,
                                       category_match: bool, price_match: bool) -> str:
        """
        Generate reasoning for why a product is recommended.
        
        Args:
            product: Product data
            query: Search query
            category_match: Whether category matches
            price_match: Whether price is in range
            
        Returns:
            Reasoning text
        """
        reasons = []
        
        # Query relevance
        if query.strip():
            reasons.append(f"matches your search for '{query}'")
        
        # Category match
        if category_match:
            reasons.append(f"is in the {product.get('category', 'requested')} category")
        
        # Price consideration
        if price_match:
            reasons.append("fits your price range")
        
        # Rating
        rating = product.get('rating')
        if rating and rating >= 4.0:
            reasons.append(f"has excellent customer ratings ({rating}/5)")
        
        # Stock availability
        stock = product.get('stock', 0)
        if stock > 0:
            if stock < 5:
                reasons.append("has limited stock available")
            else:
                reasons.append("is readily available")
        
        # Brand consideration
        brand = product.get('brand')
        if brand:
            reasons.append(f"is from {brand}")
        
        if not reasons:
            return "is a popular product in our catalog"
        
        return "This product " + ", ".join(reasons) + "."


@tool
def product_search(query: str, category: Optional[str] = None, 
                  price_range: Optional[Dict[str, float]] = None, 
                  limit: int = 10) -> ProductSearchResponse:
    """
    Search for products in the E-Com67 catalog using OpenSearch.
    
    Args:
        query: Search query string (e.g., "wireless headphones", "running shoes")
        category: Optional category filter (e.g., "electronics", "clothing")
        price_range: Optional price range with 'min' and 'max' keys (e.g., {"min": 10, "max": 100})
        limit: Maximum number of results to return (default: 10, max: 50)
        
    Returns:
        ProductSearchResponse with matching products and metadata
    """
    logger.info(f"Product search requested: query='{query}', category={category}, price_range={price_range}, limit={limit}")
    
    # Validate inputs
    if limit > 50:
        limit = 50
    if limit < 1:
        limit = 1
    
    try:
        # Initialize search tool
        search_tool = ProductSearchTool()
        
        # Build and execute search query
        search_query = search_tool.build_search_query(query, category, price_range, limit)
        
        response = get_opensearch_client().search(
            index=OPENSEARCH_INDEX,
            body=search_query
        )
        
        # Process search results
        hits = response.get("hits", {})
        total_count = hits.get("total", {}).get("value", 0)
        
        products = []
        for hit in hits.get("hits", []):
            product_data = hit["_source"]
            
            # Add search score for relevance calculation
            product_data["_score"] = hit.get("_score", 0)
            
            # Format product info
            product_info = search_tool.format_product_info(product_data)
            products.append(product_info)
        
        # Generate suggestions if no results
        suggestions = []
        if not products and query.strip():
            suggestions = search_tool.generate_search_suggestions(query)
        
        # Create response
        search_response = ProductSearchResponse(
            query=query,
            products=products,
            total_count=total_count,
            page=1,
            page_size=limit,
            suggestions=suggestions,
            filters_applied={
                "category": category,
                "price_range": price_range
            },
            has_more=total_count > limit
        )
        
        logger.info(f"Product search completed: found {len(products)} products, total {total_count}")
        
        return search_response
        
    except Exception as e:
        logger.error(f"Product search failed: {str(e)}")
        
        # Return empty response with error suggestions
        return ProductSearchResponse(
            query=query,
            products=[],
            total_count=0,
            page=1,
            page_size=limit,
            suggestions=["Try a different search term", "Browse by category", "Check spelling"],
            filters_applied={
                "category": category,
                "price_range": price_range
            },
            has_more=False
        )


@tool
def get_product_details(product_id: str) -> Optional[ProductInfo]:
    """
    Get detailed information about a specific product.
    
    Args:
        product_id: Unique product identifier
        
    Returns:
        ProductInfo with detailed product information, or None if not found
    """
    logger.info(f"Product details requested for: {product_id}")
    
    try:
        # Get product from DynamoDB
        response = get_products_table().get_item(Key={'productId': product_id})
        
        if 'Item' not in response:
            logger.warning(f"Product not found: {product_id}")
            return None
        
        product_data = response['Item']
        
        # Check if product is active
        if not product_data.get('isActive', False):
            logger.warning(f"Product is inactive: {product_id}")
            return None
        
        # Initialize search tool for formatting
        search_tool = ProductSearchTool()
        
        # Format and return product info
        product_info = search_tool.format_product_info(product_data)
        
        logger.info(f"Product details retrieved for: {product_id}")
        return product_info
        
    except ClientError as e:
        logger.error(f"Failed to get product details for {product_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting product details for {product_id}: {str(e)}")
        return None


@tool
def get_product_recommendations(query: str, category: Optional[str] = None,
                              price_range: Optional[Dict[str, float]] = None,
                              limit: int = 5) -> List[ProductRecommendation]:
    """
    Get intelligent product recommendations based on user query and preferences.
    
    Args:
        query: User's need description (e.g., "I need something for running")
        category: Optional preferred category
        price_range: Optional price range preference
        limit: Maximum number of recommendations (default: 5)
        
    Returns:
        List of ProductRecommendation with reasoning and scoring
    """
    logger.info(f"Product recommendations requested: query='{query}', category={category}, limit={limit}")
    
    try:
        # Initialize search tool
        search_tool = ProductSearchTool()
        
        # Perform broader search for recommendations
        search_limit = min(limit * 3, 30)  # Get more results to choose best recommendations from
        search_query = search_tool.build_search_query(query, category, price_range, search_limit)
        
        response = get_opensearch_client().search(
            index=OPENSEARCH_INDEX,
            body=search_query
        )
        
        # Process results into recommendations
        recommendations = []
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits[:limit]:  # Take only the requested number
            product_data = hit["_source"]
            product_data["_score"] = hit.get("_score", 0)
            
            # Format product info
            product_info = search_tool.format_product_info(product_data)
            
            # Calculate recommendation metrics
            category_match = category is None or product_data.get('category') == category
            
            price_match = True
            if price_range:
                product_price = float(product_data.get('price', 0))
                price_min = price_range.get('min', 0)
                price_max = price_range.get('max', float('inf'))
                price_match = price_min <= product_price <= price_max
            
            # Calculate relevance score
            relevance_score = search_tool.calculate_relevance_score(
                product_data, query, category_match, price_match
            )
            
            # Generate reasoning
            reasoning = search_tool.generate_recommendation_reasoning(
                product_data, query, category_match, price_match
            )
            
            # Determine confidence level
            if relevance_score >= 0.8:
                confidence_level = "high"
            elif relevance_score >= 0.5:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            # Create recommendation
            recommendation = ProductRecommendation(
                product=product_info,
                relevance_score=relevance_score,
                reasoning=reasoning,
                category_match=category_match,
                price_match=price_match,
                similarity_factors=[
                    "search_relevance" if query.strip() else "popularity",
                    "category_match" if category_match else "cross_category",
                    "price_appropriate" if price_match else "price_consideration",
                    "high_rating" if product_data.get('rating', 0) >= 4.0 else "standard_rating",
                    "in_stock" if product_data.get('stock', 0) > 0 else "limited_stock"
                ],
                confidence_level=confidence_level
            )
            
            recommendations.append(recommendation)
        
        # Sort by relevance score
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Generated {len(recommendations)} product recommendations")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate product recommendations: {str(e)}")
        return []