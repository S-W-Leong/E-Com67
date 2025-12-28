"""
Order Trends Analytics Tool

Analyzes order patterns over time including:
- Order volume aggregation by time period (day/week/month)
- Revenue trends and calculations
- Order status distribution
- Growth rate calculations

This tool is designed to be invoked by the Admin Insights Agent
to provide business intelligence on order patterns.
"""

import os
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta
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


class OrderTrendsToolInput(BaseModel):
    """Input schema for order trends analysis"""
    date_from: int = Field(..., description="Start date as Unix timestamp (seconds)")
    date_to: int = Field(..., description="End date as Unix timestamp (seconds)")
    group_by: Literal["day", "week", "month"] = Field(
        default="day",
        description="Time period grouping: day, week, or month"
    )
    metrics: List[Literal["volume", "revenue", "status_distribution"]] = Field(
        default=["volume", "revenue"],
        description="Metrics to calculate: volume, revenue, status_distribution"
    )
    
    @validator('date_to')
    def validate_date_range(cls, date_to, values):
        """Ensure date_to is after date_from"""
        date_from = values.get('date_from')
        if date_from and date_to < date_from:
            raise ValueError("date_to must be greater than or equal to date_from")
        return date_to


class OrderTrendsToolOutput(BaseModel):
    """Output schema for order trends"""
    time_series: List[Dict[str, Any]] = Field(
        description="Time-series data with metrics for each period"
    )
    summary: Dict[str, Any] = Field(
        description="Overall summary statistics"
    )
    status_breakdown: Dict[str, int] = Field(
        description="Count of orders by status"
    )
    growth_rate: Optional[float] = Field(
        None,
        description="Period-over-period growth rate percentage"
    )


def get_orders_table():
    """Get orders table with lazy initialization"""
    table_name = os.environ.get('ORDERS_TABLE_NAME', 'e-com67-orders')
    return dynamodb.Table(table_name)


@tracer.capture_method
def query_orders_by_date_range(date_from: int, date_to: int) -> List[Dict[str, Any]]:
    """
    Query all orders within a date range using scan operation.
    
    Note: Since we need orders across all users, we use scan with filter.
    For production at scale, consider using DynamoDB Streams or maintaining
    a time-series aggregation table.
    
    Args:
        date_from: Start timestamp (Unix seconds)
        date_to: End timestamp (Unix seconds)
    
    Returns:
        List of order items
    """
    logger.info("Querying orders by date range", extra={
        "date_from": date_from,
        "date_to": date_to,
        "date_from_readable": datetime.fromtimestamp(date_from).isoformat(),
        "date_to_readable": datetime.fromtimestamp(date_to).isoformat()
    })
    
    try:
        orders_table = get_orders_table()
        orders = []
        
        # Scan with filter for timestamp range
        scan_kwargs = {
            'FilterExpression': Key('timestamp').between(date_from, date_to)
        }
        
        # Handle pagination for scan
        while True:
            response = orders_table.scan(**scan_kwargs)
            orders.extend(response.get('Items', []))
            
            # Check if there are more items to scan
            if 'LastEvaluatedKey' not in response:
                break
            
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        logger.info("Orders retrieved", extra={
            "total_orders": len(orders),
            "date_from": date_from,
            "date_to": date_to
        })
        
        return orders
        
    except ClientError as e:
        logger.error("Failed to query orders", extra={
            "error": str(e),
            "date_from": date_from,
            "date_to": date_to
        })
        raise


@tracer.capture_method
def aggregate_by_time_period(
    orders: List[Dict[str, Any]],
    group_by: Literal["day", "week", "month"]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Aggregate orders by time period (day, week, or month).
    
    Args:
        orders: List of order items
        group_by: Grouping period (day, week, month)
    
    Returns:
        Dictionary mapping period keys to lists of orders
    """
    logger.info("Aggregating orders by time period", extra={
        "total_orders": len(orders),
        "group_by": group_by
    })
    
    aggregated = defaultdict(list)
    
    for order in orders:
        timestamp = order.get('timestamp', order.get('createdAt', 0))
        dt = datetime.fromtimestamp(timestamp)
        
        # Generate period key based on grouping
        if group_by == "day":
            period_key = dt.strftime("%Y-%m-%d")
        elif group_by == "week":
            # ISO week format: YYYY-Www (e.g., 2024-W01)
            year, week, _ = dt.isocalendar()
            period_key = f"{year}-W{week:02d}"
        elif group_by == "month":
            period_key = dt.strftime("%Y-%m")
        else:
            period_key = dt.strftime("%Y-%m-%d")  # Default to day
        
        aggregated[period_key].append(order)
    
    logger.info("Aggregation complete", extra={
        "periods_count": len(aggregated),
        "group_by": group_by
    })
    
    return dict(aggregated)


@tracer.capture_method
def calculate_status_distribution(orders: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculate the distribution of orders by status.
    
    Args:
        orders: List of order items
    
    Returns:
        Dictionary mapping status to count
    """
    logger.info("Calculating status distribution", extra={
        "total_orders": len(orders)
    })
    
    status_counts = defaultdict(int)
    
    for order in orders:
        status = order.get('status', 'unknown')
        status_counts[status] += 1
    
    result = dict(status_counts)
    
    logger.info("Status distribution calculated", extra={
        "status_breakdown": result
    })
    
    return result


@tracer.capture_method
def calculate_growth_rate(
    current_period_orders: List[Dict[str, Any]],
    previous_period_orders: List[Dict[str, Any]]
) -> float:
    """
    Calculate period-over-period growth rate.
    
    Formula: ((current - previous) / previous) * 100
    
    Args:
        current_period_orders: Orders in current period
        previous_period_orders: Orders in previous period
    
    Returns:
        Growth rate as percentage
    """
    current_count = len(current_period_orders)
    previous_count = len(previous_period_orders)
    
    if previous_count == 0:
        # If no previous orders, return 100% growth if current has orders, else 0%
        return 100.0 if current_count > 0 else 0.0
    
    growth_rate = ((current_count - previous_count) / previous_count) * 100
    
    logger.info("Growth rate calculated", extra={
        "current_count": current_count,
        "previous_count": previous_count,
        "growth_rate": growth_rate
    })
    
    return round(growth_rate, 2)


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
def analyze_order_trends(input_data: OrderTrendsToolInput) -> OrderTrendsToolOutput:
    """
    Main function to analyze order trends based on input parameters.
    
    Args:
        input_data: Validated input parameters
    
    Returns:
        OrderTrendsToolOutput with analysis results
    """
    logger.info("Starting order trends analysis", extra={
        "date_from": input_data.date_from,
        "date_to": input_data.date_to,
        "group_by": input_data.group_by,
        "metrics": input_data.metrics
    })
    
    # Query orders in date range
    orders = query_orders_by_date_range(input_data.date_from, input_data.date_to)
    
    # Convert Decimals to floats
    orders = convert_decimals_to_float(orders)
    
    # Aggregate by time period
    aggregated_orders = aggregate_by_time_period(orders, input_data.group_by)
    
    # Build time series data
    time_series = []
    for period_key in sorted(aggregated_orders.keys()):
        period_orders = aggregated_orders[period_key]
        period_data = {
            "period": period_key,
            "timestamp": period_orders[0].get('timestamp', period_orders[0].get('createdAt', 0))
        }
        
        # Calculate requested metrics
        if "volume" in input_data.metrics:
            period_data["order_count"] = len(period_orders)
        
        if "revenue" in input_data.metrics:
            total_revenue = sum(
                float(order.get('total', 0)) for order in period_orders
            )
            period_data["total_revenue"] = round(total_revenue, 2)
            period_data["average_order_value"] = (
                round(total_revenue / len(period_orders), 2) if period_orders else 0
            )
        
        if "status_distribution" in input_data.metrics:
            period_data["status_breakdown"] = calculate_status_distribution(period_orders)
        
        time_series.append(period_data)
    
    # Calculate overall summary
    total_orders = len(orders)
    total_revenue = sum(float(order.get('total', 0)) for order in orders)
    
    summary = {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders > 0 else 0,
        "date_range": {
            "from": input_data.date_from,
            "to": input_data.date_to,
            "from_readable": datetime.fromtimestamp(input_data.date_from).isoformat(),
            "to_readable": datetime.fromtimestamp(input_data.date_to).isoformat()
        }
    }
    
    # Calculate overall status breakdown
    status_breakdown = calculate_status_distribution(orders)
    
    # Calculate growth rate (compare first and last periods)
    growth_rate = None
    if len(time_series) >= 2:
        sorted_periods = sorted(aggregated_orders.keys())
        first_period_orders = aggregated_orders[sorted_periods[0]]
        last_period_orders = aggregated_orders[sorted_periods[-1]]
        growth_rate = calculate_growth_rate(last_period_orders, first_period_orders)
    
    logger.info("Order trends analysis complete", extra={
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "periods_analyzed": len(time_series),
        "growth_rate": growth_rate
    })
    
    return OrderTrendsToolOutput(
        time_series=time_series,
        summary=summary,
        status_breakdown=status_breakdown,
        growth_rate=growth_rate
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for Order Trends Analytics Tool.
    
    Expected event format:
    {
        "date_from": 1234567890,
        "date_to": 1234567890,
        "group_by": "day",
        "metrics": ["volume", "revenue"]
    }
    """
    logger.info("Order Trends Tool invoked", extra={"event": event})
    
    try:
        # Parse and validate input
        input_data = OrderTrendsToolInput(**event)
        
        # Perform analysis
        result = analyze_order_trends(input_data)
        
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
                "message": "Failed to query order data"
            })
        }
    
    except Exception as e:
        logger.exception("Unexpected error in Order Trends Tool")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            })
        }
