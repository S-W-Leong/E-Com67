/**
 * Analytics Message Formatter
 * 
 * Formats analytics data from the Admin Insights Agent into visual components.
 * Detects data types (metrics, trends, product lists) and renders them with
 * appropriate styling and interactivity.
 * 
 * Requirements: 1.4, 2.1, 2.2, 2.3, 3.1, 3.2
 */

import React from 'react'
import { TrendingUp, TrendingDown, Package, DollarSign, ShoppingCart, BarChart3, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Detect if message contains structured analytics data
 */
export const detectAnalyticsData = (content) => {
  try {
    // Try to parse as JSON
    const data = JSON.parse(content)
    
    if (data.type === 'order_trends') return { type: 'order_trends', data }
    if (data.type === 'sales_insights') return { type: 'sales_insights', data }
    if (data.type === 'product_search') return { type: 'product_search', data }
    if (data.type === 'metrics') return { type: 'metrics', data }
    
    return null
  } catch {
    return null
  }
}

/**
 * Format a metric value with appropriate units
 */
const formatMetric = (value, type) => {
  if (type === 'currency') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value)
  }
  
  if (type === 'percentage') {
    return `${value.toFixed(1)}%`
  }
  
  if (type === 'number') {
    return new Intl.NumberFormat('en-US').format(value)
  }
  
  return value
}

/**
 * Metric Card Component
 */
const MetricCard = ({ label, value, type = 'number', trend = null, icon: Icon }) => {
  const trendColor = trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-600'
  const TrendIcon = trend > 0 ? TrendingUp : TrendingDown
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500 font-medium">{label}</span>
        {Icon && <Icon className="h-4 w-4 text-gray-400" />}
      </div>
      <div className="flex items-end justify-between">
        <span className="text-lg font-bold text-gray-900">
          {formatMetric(value, type)}
        </span>
        {trend !== null && (
          <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
            <TrendIcon className="h-3 w-3" />
            <span>{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Order Trends Formatter
 */
export const OrderTrendsFormatter = ({ data }) => {
  const { summary, status_breakdown, time_series } = data
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="h-4 w-4 text-primary-600" />
        <span className="text-sm font-semibold text-gray-900">Order Trends</span>
      </div>
      
      {/* Summary Metrics */}
      {summary && (
        <div className="grid grid-cols-2 gap-2">
          {summary.total_orders !== undefined && (
            <MetricCard
              label="Total Orders"
              value={summary.total_orders}
              type="number"
              trend={summary.growth_rate}
              icon={ShoppingCart}
            />
          )}
          {summary.total_revenue !== undefined && (
            <MetricCard
              label="Total Revenue"
              value={summary.total_revenue}
              type="currency"
              icon={DollarSign}
            />
          )}
          {summary.average_order_value !== undefined && (
            <MetricCard
              label="Avg Order Value"
              value={summary.average_order_value}
              type="currency"
            />
          )}
        </div>
      )}
      
      {/* Status Breakdown */}
      {status_breakdown && Object.keys(status_breakdown).length > 0 && (
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
          <div className="text-xs font-medium text-gray-700 mb-2">Order Status</div>
          <div className="space-y-1">
            {Object.entries(status_breakdown).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between text-xs">
                <span className="text-gray-600 capitalize">{status}</span>
                <span className="font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Time Series Preview */}
      {time_series && time_series.length > 0 && (
        <div className="text-xs text-gray-500">
          Showing data for {time_series.length} time periods
        </div>
      )}
    </div>
  )
}

/**
 * Sales Insights Formatter
 */
export const SalesInsightsFormatter = ({ data }) => {
  const { top_products, category_performance, insights } = data
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <Package className="h-4 w-4 text-primary-600" />
        <span className="text-sm font-semibold text-gray-900">Sales Insights</span>
      </div>
      
      {/* Top Products */}
      {top_products && top_products.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
            <span className="text-xs font-medium text-gray-700">Top Products</span>
          </div>
          <div className="divide-y divide-gray-100">
            {top_products.slice(0, 5).map((product, index) => (
              <div key={product.productId || index} className="px-3 py-2 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/products/edit/${product.productId}`}
                      className="text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline flex items-center gap-1"
                    >
                      <span className="truncate">{product.name || product.productId}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0" />
                    </Link>
                    {product.category && (
                      <div className="text-xs text-gray-500 mt-0.5">{product.category}</div>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0">
                    {product.revenue !== undefined && (
                      <div className="text-xs font-semibold text-gray-900">
                        {formatMetric(product.revenue, 'currency')}
                      </div>
                    )}
                    {product.units_sold !== undefined && (
                      <div className="text-xs text-gray-500">
                        {product.units_sold} sold
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Category Performance */}
      {category_performance && Object.keys(category_performance).length > 0 && (
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
          <div className="text-xs font-medium text-gray-700 mb-2">Category Performance</div>
          <div className="space-y-1">
            {Object.entries(category_performance).slice(0, 5).map(([category, metrics]) => (
              <div key={category} className="flex items-center justify-between text-xs">
                <span className="text-gray-600 capitalize">{category}</span>
                <span className="font-medium text-gray-900">
                  {formatMetric(metrics.revenue || metrics.total_revenue || 0, 'currency')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Insights */}
      {insights && insights.length > 0 && (
        <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
          <div className="text-xs font-medium text-blue-900 mb-1">Key Insights</div>
          <ul className="space-y-1">
            {insights.map((insight, index) => (
              <li key={index} className="text-xs text-blue-800">• {insight}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/**
 * Product Search Results Formatter
 */
export const ProductSearchFormatter = ({ data }) => {
  const { products, total_results } = data
  
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Package className="h-4 w-4 text-primary-600" />
          <span className="text-sm font-semibold text-gray-900">Product Search</span>
        </div>
        {total_results !== undefined && (
          <span className="text-xs text-gray-500">{total_results} results</span>
        )}
      </div>
      
      {products && products.length > 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-100">
            {products.map((product, index) => (
              <div key={product.productId || index} className="px-3 py-2 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/products/edit/${product.productId}`}
                      className="text-xs font-medium text-primary-600 hover:text-primary-700 hover:underline flex items-center gap-1"
                    >
                      <span className="truncate">{product.name}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0" />
                    </Link>
                    {product.description && (
                      <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                        {product.description}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      {product.category && (
                        <span className="text-xs text-gray-500">{product.category}</span>
                      )}
                      {product.stock !== undefined && (
                        <span className={`text-xs ${product.stock > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}
                        </span>
                      )}
                    </div>
                  </div>
                  {product.price !== undefined && (
                    <div className="text-xs font-semibold text-gray-900 flex-shrink-0">
                      {formatMetric(product.price, 'currency')}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-xs text-gray-500 text-center py-4">
          No products found
        </div>
      )}
    </div>
  )
}

/**
 * Generic Metrics Formatter
 */
export const MetricsFormatter = ({ data }) => {
  const { metrics } = data
  
  if (!metrics || metrics.length === 0) {
    return null
  }
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="h-4 w-4 text-primary-600" />
        <span className="text-sm font-semibold text-gray-900">Metrics</span>
      </div>
      
      <div className="grid grid-cols-2 gap-2">
        {metrics.map((metric, index) => (
          <MetricCard
            key={index}
            label={metric.label}
            value={metric.value}
            type={metric.type || 'number'}
            trend={metric.trend}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * Main formatter component that detects and renders appropriate format
 */
export const AnalyticsMessageFormatter = ({ content }) => {
  const analyticsData = detectAnalyticsData(content)
  
  if (!analyticsData) {
    // Return plain text if not analytics data
    return <div className="text-sm whitespace-pre-wrap">{content}</div>
  }
  
  // Render appropriate formatter based on data type
  switch (analyticsData.type) {
    case 'order_trends':
      return <OrderTrendsFormatter data={analyticsData.data} />
    
    case 'sales_insights':
      return <SalesInsightsFormatter data={analyticsData.data} />
    
    case 'product_search':
      return <ProductSearchFormatter data={analyticsData.data} />
    
    case 'metrics':
      return <MetricsFormatter data={analyticsData.data} />
    
    default:
      return <div className="text-sm whitespace-pre-wrap">{content}</div>
  }
}

export default AnalyticsMessageFormatter
