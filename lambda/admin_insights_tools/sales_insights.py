"""
Sales Insights Analytics Tool

Analyzes product sales performance including:
- Product ranking by revenue or units sold
- Product revenue aggregation from order line items
- Category-based performance analysis
- Low performer identification
- Product-specific time-series trends

This tool is designed to be invoked by the Admin Insights Agent
to provide business intelligence on product sales.
"""

import os
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, validator

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-southeast-1'))


class SalesInsightsToolInput(BaseModel):
    """Input schema for sales insights analysis"""
    date_from: int = Field(..., description="Start date as Unix timestamp (seconds)")
    date_to: int = Field(..., description="End date as Unix timestamp (seconds)")
    category: Optional[str] = Field(None, description="Filter by product category")
    sort_by: Literal["revenue", "units_sold", "growth"] = Field(
        default="revenue",
        description="Sort products by: revenue, units_sold, or growth"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of products to return (1-100)"
    )
    low_performer_threshold: Optional[float] = Field(
        None,
        description="Revenue threshold for identifying low performers"
    )
    
    @validator('date_to')
    def validate_date_range(cls, date_to, values):
        """Ensure date_to is after date_from"""
        date_from = values.get('date_from')
        if date_from and date_to < date_from:
            raise ValueError("date_to must be greater than or equal to date_from")
        return date_to


class ProductPerformance(BaseModel):
    """Product sales performance metrics"""
    product_id: str
    product_name: str
    category: str
    units_sold: int
    total_revenue: float
    average_price: float
    order_count: int


class SalesInsightsToolOutput(BaseModel):
    """Output schema for sales insights"""
    top_products: List[ProductPerformance] = Field(
        description="Top performing products based on sort criteria"
    )
    category_performance: Dict[str, Dict[str, Any]] = Field(
        description="Sales metrics aggregated by category"
    )
    low_performers: List[ProductPerformance] = Field(
        description="Products with sales below threshold"
    )
    insights: List[str] = Field(
        description="Human-readable insights and observations"
    )
    summary: Dict[str, Any] = Field(
        description="Overall sales summary statistics"
    )


def get_orders_table():
    """Get orders table with lazy initialization"""
    table_name = os.environ.get('ORDERS_TABLE_NAME', 'e-com67-orders')
    return dynamodb.Table(table_name)


def get_products_table():
    """Get products table with lazy initialization"""
    table_name = os.environ.get('PRODUCTS_TABLE_NAME', 'e-com67-products')
    return dynamodb.Table(table_name)


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
def query_order_line_items(date_from: int, date_to: int) -> List[Dict[str, Any]]:
    """
    Query all orders within a date range and extract line items.
    
    Each order contains an 'items' array with product details:
    - productId: Product identifier
    - name: Product name
    - price: Unit price
    - quantity: Quantity ordered
    - category: Product category (if available)
    
    Args:
        date_from: Start timestamp (Unix seconds)
        date_to: End timestamp (Unix seconds)
    
    Returns:
        List of order line items with order context
    """
    logger.info("Querying order line items", extra={
        "date_from": date_from,
        "date_to": date_to,
        "date_from_readable": datetime.fromtimestamp(date_from).isoformat(),
        "date_to_readable": datetime.fromtimestamp(date_to).isoformat()
    })
    
    try:
        orders_table = get_orders_table()
        line_items = []
        
        # Scan with filter for timestamp range
        scan_kwargs = {
            'FilterExpression': Key('timestamp').between(date_from, date_to)
        }
        
        # Handle pagination for scan
        while True:
            response = orders_table.scan(**scan_kwargs)
            orders = response.get('Items', [])
            
            # Extract line items from each order
            for order in orders:
                order_id = order.get('orderId')
                order_timestamp = order.get('timestamp', order.get('createdAt', 0))
                items = order.get('items', [])
                
                for item in items:
                    # Enrich line item with order context
                    line_item = {
                        'orderId': order_id,
                        'orderTimestamp': order_timestamp,
                        'productId': item.get('productId'),
                        'productName': item.get('name', 'Unknown'),
                        'category': item.get('category', 'Uncategorized'),
                        'price': float(item.get('price', 0)),
                        'quantity': int(item.get('quantity', 0)),
                        'lineTotal': float(item.get('price', 0)) * int(item.get('quantity', 0))
                    }
                    line_items.append(line_item)
            
            # Check if there are more items to scan
            if 'LastEvaluatedKey' not in response:
                break
            
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        logger.info("Order line items retrieved", extra={
            "total_line_items": len(line_items),
            "date_from": date_from,
            "date_to": date_to
        })
        
        return line_items
        
    except ClientError as e:
        logger.error("Failed to query order line items", extra={
            "error": str(e),
            "date_from": date_from,
            "date_to": date_to
        })
        raise


@tracer.capture_method
def calculate_product_revenue(line_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate total revenue and units sold per product.
    
    Aggregates line items by productId to compute:
    - Total revenue (sum of price * quantity)
    - Total units sold
    - Number of orders containing the product
    - Average price per unit
    
    Args:
        line_items: List of order line items
    
    Returns:
        Dictionary mapping productId to aggregated metrics
    """
    logger.info("Calculating product revenue", extra={
        "total_line_items": len(line_items)
    })
    
    product_metrics = defaultdict(lambda: {
        'productId': '',
        'productName': '',
        'category': '',
        'totalRevenue': 0.0,
        'unitsSold': 0,
        'orderCount': 0,
        'orders': set(),
        'prices': []
    })
    
    for item in line_items:
        product_id = item['productId']
        metrics = product_metrics[product_id]
        
        # Set product details (use first occurrence)
        if not metrics['productId']:
            metrics['productId'] = product_id
            metrics['productName'] = item['productName']
            metrics['category'] = item['category']
        
        # Aggregate metrics
        metrics['totalRevenue'] += item['lineTotal']
        metrics['unitsSold'] += item['quantity']
        metrics['orders'].add(item['orderId'])
        metrics['prices'].append(item['price'])
    
    # Calculate derived metrics and clean up
    result = {}
    for product_id, metrics in product_metrics.items():
        result[product_id] = {
            'productId': metrics['productId'],
            'productName': metrics['productName'],
            'category': metrics['category'],
            'totalRevenue': round(metrics['totalRevenue'], 2),
            'unitsSold': metrics['unitsSold'],
            'orderCount': len(metrics['orders']),
            'averagePrice': round(sum(metrics['prices']) / len(metrics['prices']), 2) if metrics['prices'] else 0.0
        }
    
    logger.info("Product revenue calculated", extra={
        "unique_products": len(result)
    })
    
    return result


@tracer.capture_method
def rank_products(
    product_metrics: Dict[str, Dict[str, Any]],
    sort_by: Literal["revenue", "units_sold", "growth"],
    limit: int
) -> List[ProductPerformance]:
    """
    Rank products by specified metric and return top N.
    
    Args:
        product_metrics: Dictionary of product metrics
        sort_by: Metric to sort by (revenue, units_sold, growth)
        limit: Maximum number of products to return
    
    Returns:
        List of top performing products
    """
    logger.info("Ranking products", extra={
        "sort_by": sort_by,
        "limit": limit,
        "total_products": len(product_metrics)
    })
    
    # Convert to list for sorting
    products = list(product_metrics.values())
    
    # Sort by specified metric
    if sort_by == "revenue":
        products.sort(key=lambda p: p['totalRevenue'], reverse=True)
    elif sort_by == "units_sold":
        products.sort(key=lambda p: p['unitsSold'], reverse=True)
    elif sort_by == "growth":
        # Growth calculation would require historical data comparison
        # For now, sort by revenue as a proxy
        logger.warning("Growth sorting not yet implemented, using revenue as fallback")
        products.sort(key=lambda p: p['totalRevenue'], reverse=True)
    
    # Take top N products
    top_products = products[:limit]
    
    # Convert to ProductPerformance models
    result = [
        ProductPerformance(
            product_id=p['productId'],
            product_name=p['productName'],
            category=p['category'],
            units_sold=p['unitsSold'],
            total_revenue=p['totalRevenue'],
            average_price=p['averagePrice'],
            order_count=p['orderCount']
        )
        for p in top_products
    ]
    
    logger.info("Products ranked", extra={
        "returned_count": len(result),
        "sort_by": sort_by
    })
    
    return result


@tracer.capture_method
def aggregate_by_category(
    line_items: List[Dict[str, Any]],
    category_filter: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate sales metrics by product category.
    
    Args:
        line_items: List of order line items
        category_filter: Optional category to filter by
    
    Returns:
        Dictionary mapping category to aggregated metrics
    """
    logger.info("Aggregating by category", extra={
        "total_line_items": len(line_items),
        "category_filter": category_filter
    })
    
    # Filter by category if specified
    if category_filter:
        line_items = [item for item in line_items if item['category'] == category_filter]
        logger.info("Filtered by category", extra={
            "category": category_filter,
            "filtered_count": len(line_items)
        })
    
    category_metrics = defaultdict(lambda: {
        'totalRevenue': 0.0,
        'unitsSold': 0,
        'orderCount': 0,
        'productCount': set(),
        'orders': set()
    })
    
    for item in line_items:
        category = item['category']
        metrics = category_metrics[category]
        
        metrics['totalRevenue'] += item['lineTotal']
        metrics['unitsSold'] += item['quantity']
        metrics['productCount'].add(item['productId'])
        metrics['orders'].add(item['orderId'])
    
    # Calculate derived metrics and clean up
    result = {}
    for category, metrics in category_metrics.items():
        result[category] = {
            'totalRevenue': round(metrics['totalRevenue'], 2),
            'unitsSold': metrics['unitsSold'],
            'orderCount': len(metrics['orders']),
            'productCount': len(metrics['productCount']),
            'averageRevenuePerProduct': round(
                metrics['totalRevenue'] / len(metrics['productCount']), 2
            ) if metrics['productCount'] else 0.0
        }
    
    logger.info("Category aggregation complete", extra={
        "categories_count": len(result)
    })
    
    return result


@tracer.capture_method
def identify_low_performers(
    product_metrics: Dict[str, Dict[str, Any]],
    threshold: Optional[float] = None
) -> List[ProductPerformance]:
    """
    Identify products with sales below specified threshold.
    
    If no threshold is provided, uses the bottom 10% of products by revenue.
    
    Args:
        product_metrics: Dictionary of product metrics
        threshold: Revenue threshold for low performers
    
    Returns:
        List of low performing products
    """
    logger.info("Identifying low performers", extra={
        "threshold": threshold,
        "total_products": len(product_metrics)
    })
    
    products = list(product_metrics.values())
    
    # If no threshold provided, calculate bottom 10%
    if threshold is None:
        if not products:
            return []
        
        revenues = sorted([p['totalRevenue'] for p in products])
        percentile_10_index = max(0, int(len(revenues) * 0.1) - 1)
        threshold = revenues[percentile_10_index]
        
        logger.info("Calculated threshold from bottom 10%", extra={
            "threshold": threshold
        })
    
    # Filter products below threshold
    low_performers = [p for p in products if p['totalRevenue'] < threshold]
    
    # Sort by revenue (lowest first)
    low_performers.sort(key=lambda p: p['totalRevenue'])
    
    # Convert to ProductPerformance models
    result = [
        ProductPerformance(
            product_id=p['productId'],
            product_name=p['productName'],
            category=p['category'],
            units_sold=p['unitsSold'],
            total_revenue=p['totalRevenue'],
            average_price=p['averagePrice'],
            order_count=p['orderCount']
        )
        for p in low_performers
    ]
    
    logger.info("Low performers identified", extra={
        "count": len(result),
        "threshold": threshold
    })
    
    return result


@tracer.capture_method
def generate_insights(
    top_products: List[ProductPerformance],
    category_performance: Dict[str, Dict[str, Any]],
    low_performers: List[ProductPerformance],
    summary: Dict[str, Any]
) -> List[str]:
    """
    Generate human-readable insights from sales data.
    
    Args:
        top_products: Top performing products
        category_performance: Category aggregated metrics
        low_performers: Low performing products
        summary: Overall summary statistics
    
    Returns:
        List of insight strings
    """
    insights = []
    
    # Top product insight
    if top_products:
        top_product = top_products[0]
        insights.append(
            f"Top product: '{top_product.product_name}' generated "
            f"${top_product.total_revenue:,.2f} in revenue with {top_product.units_sold} units sold"
        )
    
    # Category insight
    if category_performance:
        top_category = max(
            category_performance.items(),
            key=lambda x: x[1]['totalRevenue']
        )
        insights.append(
            f"Best performing category: '{top_category[0]}' with "
            f"${top_category[1]['totalRevenue']:,.2f} in revenue"
        )
    
    # Low performer insight
    if low_performers:
        insights.append(
            f"{len(low_performers)} products identified as low performers, "
            f"requiring attention or potential discontinuation"
        )
    
    # Overall performance insight
    total_revenue = summary.get('total_revenue', 0)
    unique_products = summary.get('unique_products_sold', 0)
    if unique_products > 0:
        avg_revenue_per_product = total_revenue / unique_products
        insights.append(
            f"Average revenue per product: ${avg_revenue_per_product:,.2f} "
            f"across {unique_products} products"
        )
    
    return insights


@tracer.capture_method
def analyze_sales_insights(input_data: SalesInsightsToolInput) -> SalesInsightsToolOutput:
    """
    Main function to analyze sales insights based on input parameters.
    
    Args:
        input_data: Validated input parameters
    
    Returns:
        SalesInsightsToolOutput with analysis results
    """
    logger.info("Starting sales insights analysis", extra={
        "date_from": input_data.date_from,
        "date_to": input_data.date_to,
        "category": input_data.category,
        "sort_by": input_data.sort_by,
        "limit": input_data.limit
    })
    
    # Query order line items in date range
    line_items = query_order_line_items(input_data.date_from, input_data.date_to)
    
    # Convert Decimals to floats
    line_items = convert_decimals_to_float(line_items)
    
    # Filter by category if specified
    if input_data.category:
        line_items = [item for item in line_items if item['category'] == input_data.category]
        logger.info("Filtered by category", extra={
            "category": input_data.category,
            "filtered_count": len(line_items)
        })
    
    # Calculate product revenue metrics
    product_metrics = calculate_product_revenue(line_items)
    
    # Rank products
    top_products = rank_products(product_metrics, input_data.sort_by, input_data.limit)
    
    # Aggregate by category
    category_performance = aggregate_by_category(line_items, input_data.category)
    
    # Identify low performers
    low_performers = identify_low_performers(
        product_metrics,
        input_data.low_performer_threshold
    )
    
    # Calculate summary statistics
    total_revenue = sum(p['totalRevenue'] for p in product_metrics.values())
    total_units = sum(p['unitsSold'] for p in product_metrics.values())
    unique_products = len(product_metrics)
    
    summary = {
        'total_revenue': round(total_revenue, 2),
        'total_units_sold': total_units,
        'unique_products_sold': unique_products,
        'average_revenue_per_product': round(total_revenue / unique_products, 2) if unique_products > 0 else 0.0,
        'date_range': {
            'from': input_data.date_from,
            'to': input_data.date_to,
            'from_readable': datetime.fromtimestamp(input_data.date_from).isoformat(),
            'to_readable': datetime.fromtimestamp(input_data.date_to).isoformat()
        }
    }
    
    # Generate insights
    insights = generate_insights(top_products, category_performance, low_performers, summary)
    
    logger.info("Sales insights analysis complete", extra={
        "total_revenue": total_revenue,
        "unique_products": unique_products,
        "top_products_count": len(top_products),
        "low_performers_count": len(low_performers)
    })
    
    return SalesInsightsToolOutput(
        top_products=top_products,
        category_performance=category_performance,
        low_performers=low_performers,
        insights=insights,
        summary=summary
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for Sales Insights Analytics Tool.
    
    Expected event format:
    {
        "date_from": 1234567890,
        "date_to": 1234567890,
        "category": "Electronics",
        "sort_by": "revenue",
        "limit": 10,
        "low_performer_threshold": 100.0
    }
    """
    logger.info("Sales Insights Tool invoked", extra={"event": event})
    
    try:
        # Parse and validate input
        input_data = SalesInsightsToolInput(**event)
        
        # Perform analysis
        result = analyze_sales_insights(input_data)
        
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
    
    except ClientError as e:
        logger.error("DynamoDB error", extra={"error": str(e)})
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "DATABASE_ERROR",
                "message": "Failed to query sales data"
            })
        }
    
    except Exception as e:
        logger.exception("Unexpected error in Sales Insights Tool")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            })
        }
