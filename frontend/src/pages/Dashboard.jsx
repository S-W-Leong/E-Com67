import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Package, 
  ShoppingCart, 
  DollarSign, 
  TrendingUp,
  Plus,
  Eye,
  AlertTriangle
} from 'lucide-react'
import { analyticsAPI, productAPI, orderAPI } from '../services/api'

const Dashboard = () => {
  const [metrics, setMetrics] = useState({
    totalProducts: 0,
    totalOrders: 0,
    totalRevenue: 0,
    recentOrders: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load basic metrics
      const [productsResponse, ordersResponse] = await Promise.allSettled([
        productAPI.getProducts({ limit: 1 }),
        orderAPI.getOrders({ limit: 5 })
      ])

      // Calculate metrics from available data
      const totalProducts = productsResponse.status === 'fulfilled' 
        ? productsResponse.value.count || 0 
        : 0

      const recentOrders = ordersResponse.status === 'fulfilled'
        ? ordersResponse.value.orders || []
        : []

      const totalOrders = recentOrders.length
      const totalRevenue = recentOrders.reduce((sum, order) => sum + (order.totalAmount || 0), 0)

      setMetrics({
        totalProducts,
        totalOrders,
        totalRevenue,
        recentOrders: recentOrders.slice(0, 5)
      })

    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      shipped: 'bg-purple-100 text-purple-800',
      delivered: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      failed: 'bg-red-100 text-red-800'
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
          <p className="text-red-700">{error}</p>
        </div>
        <button 
          onClick={loadDashboardData}
          className="mt-2 btn-primary text-sm"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Overview of your e-commerce platform</p>
        </div>
        <div className="flex space-x-3">
          <Link to="/products/new" className="btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Add Product
          </Link>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Package className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Products</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.totalProducts}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <ShoppingCart className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Recent Orders</p>
              <p className="text-2xl font-bold text-gray-900">{metrics.totalOrders}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <DollarSign className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Revenue (Recent)</p>
              <p className="text-2xl font-bold text-gray-900">{formatCurrency(metrics.totalRevenue)}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Growth</p>
              <p className="text-2xl font-bold text-gray-900">+12%</p>
              <p className="text-xs text-gray-500">vs last month</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Orders */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Orders</h2>
            <Link 
              to="/orders" 
              className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center"
            >
              View all
              <Eye className="h-4 w-4 ml-1" />
            </Link>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          {metrics.recentOrders.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="table-header">
                <tr>
                  <th className="px-6 py-3 text-left">Order ID</th>
                  <th className="px-6 py-3 text-left">Customer</th>
                  <th className="px-6 py-3 text-left">Status</th>
                  <th className="px-6 py-3 text-left">Total</th>
                  <th className="px-6 py-3 text-left">Date</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {metrics.recentOrders.map((order) => (
                  <tr key={order.orderId} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-gray-900">
                        {order.orderId.slice(0, 8)}...
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">
                        {order.userId.slice(0, 8)}...
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(order.status)}`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-medium text-gray-900">
                        {formatCurrency(order.totalAmount)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-500">
                        {formatDate(order.createdAt)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-8 text-center">
              <ShoppingCart className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No recent orders found</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link to="/products" className="card p-6 hover:shadow-lg transition-shadow duration-200">
          <div className="flex items-center">
            <Package className="h-8 w-8 text-primary-600" />
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Manage Products</h3>
              <p className="text-gray-600">Add, edit, or remove products from your catalog</p>
            </div>
          </div>
        </Link>

        <Link to="/orders" className="card p-6 hover:shadow-lg transition-shadow duration-200">
          <div className="flex items-center">
            <ShoppingCart className="h-8 w-8 text-primary-600" />
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">View Orders</h3>
              <p className="text-gray-600">Track and manage customer orders</p>
            </div>
          </div>
        </Link>

        <div className="card p-6 opacity-50">
          <div className="flex items-center">
            <TrendingUp className="h-8 w-8 text-gray-400" />
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-500">Analytics</h3>
              <p className="text-gray-400">Coming soon - detailed analytics and reports</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard