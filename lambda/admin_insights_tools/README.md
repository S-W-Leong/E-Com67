# Admin Insights Tools

This directory contains custom analytics tools that query DynamoDB and OpenSearch to compute sales and order metrics.

## Structure

- `order_trends.py` - Order trends analytics tool
- `sales_insights.py` - Sales insights analytics tool
- `product_search.py` - Product search tool using OpenSearch

## Tools

### Order Trends Tool
Analyzes order patterns over time including:
- Order volume by time period
- Status distribution
- Revenue trends
- Growth rates

### Sales Insights Tool
Analyzes product sales performance including:
- Top-selling products
- Product revenue calculations
- Category-based aggregations
- Low performer identification

### Product Search Tool
Searches products using OpenSearch with:
- Semantic search capabilities
- Category filtering
- Relevance scoring

## Data Sources

- **DynamoDB**: e-com67-orders and e-com67-products tables
- **OpenSearch**: e-com67-products domain

## Testing

Property-based tests are located in `tests/test_admin_insights_tools.py` using the Hypothesis framework.
