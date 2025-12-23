import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { Package, ChevronRight, AlertCircle, CheckCircle, Clock, Truck, ArrowLeft } from 'lucide-react'
import { orderApi } from '../services/api'

/**
 * Get status badge styling and icon
 */
const getStatusDisplay = (status) => {
  const displays = {
    PENDING: {
      color: 'bg-yellow-100 text-yellow-800',
      icon: Clock,
      label: 'Pending'
    },
    PROCESSING: {
      color: 'bg-blue-100 text-blue-800',
      icon: Package,
      label: 'Processing'
    },
    SHIPPED: {
      color: 'bg-purple-100 text-purple-800',
      icon: Truck,
      label: 'Shipped'
    },
    DELIVERED: {
      color: 'bg-green-100 text-green-800',
      icon: CheckCircle,
      label: 'Delivered'
    },
    CANCELLED: {
      color: 'bg-red-100 text-red-800',
      icon: AlertCircle,
      label: 'Cancelled'
    }
  }
  return displays[status] || displays.PENDING
}

/**
 * Order Detail Component
 * Shows detailed information for a single order
 */
const OrderDetail = ({ orderId: propOrderId }) => {
  const { id: paramOrderId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()

  const orderId = propOrderId || paramOrderId
  const [order, setOrder] = useState(location.state?.order || null)
  const [loading, setLoading] = useState(!location.state?.order)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!order && orderId) {
      fetchOrder()
    }
  }, [orderId])

  const fetchOrder = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await orderApi.getOrder(orderId)
      setOrder(data)
    } catch (err) {
      console.error('Error fetching order:', err)
      setError('Failed to load order details. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-start gap-3">
        <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-red-800 font-semibold mb-1">Error Loading Order</h3>
          <p className="text-red-700">{error}</p>
          <button
            onClick={fetchOrder}
            className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!order) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Order not found</p>
      </div>
    )
  }

  const statusDisplay = getStatusDisplay(order.status)
  const StatusIcon = statusDisplay.icon

  return (
    <div className="max-w-4xl mx-auto">
      {/* Success Message from Checkout */}
      {location.state?.fromCheckout && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-green-800 font-semibold mb-1">Order Placed Successfully!</h3>
              <p className="text-green-700">
                Your order has been received and is being processed. You'll receive an email confirmation shortly.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={() => navigate('/orders')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="h-5 w-5" />
        Back to Orders
      </button>

      {/* Order Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Order #{order.orderId?.slice(0, 8)}</h1>
            <p className="text-gray-600">
              Placed on {new Date(order.createdAt || order.timestamp).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </p>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${statusDisplay.color}`}>
            <StatusIcon className="h-4 w-4" />
            <span className="font-medium">{statusDisplay.label}</span>
          </div>
        </div>

        {/* Shipping Address */}
        {order.shippingAddress && (
          <div className="border-t border-gray-200 pt-4">
            <h3 className="font-semibold text-gray-900 mb-2">Shipping Address</h3>
            <p className="text-gray-700">{order.shippingAddress.fullName}</p>
            <p className="text-gray-700">{order.shippingAddress.address}</p>
            <p className="text-gray-700">
              {order.shippingAddress.city}, {order.shippingAddress.state} {order.shippingAddress.zipCode}
            </p>
            <p className="text-gray-700 mt-2">{order.shippingAddress.email}</p>
            <p className="text-gray-700">{order.shippingAddress.phone}</p>
          </div>
        )}
      </div>

      {/* Order Items */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Order Items</h2>
        <div className="space-y-4">
          {order.items?.map((item, index) => (
            <div key={index} className="flex gap-4 pb-4 border-b border-gray-200 last:border-0 last:pb-0">
              <img
                src={item.imageUrl || 'https://via.placeholder.com/80x80'}
                alt={item.name}
                className="w-20 h-20 object-cover rounded-md"
              />
              <div className="flex-1">
                <Link
                  to={`/products/${item.productId}`}
                  className="font-semibold text-gray-900 hover:text-blue-600"
                >
                  {item.name}
                </Link>
                <p className="text-gray-600 text-sm mt-1">
                  Quantity: {item.quantity}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-gray-900">${(item.price * item.quantity).toFixed(2)}</p>
                <p className="text-gray-600 text-sm">${item.price.toFixed(2)} each</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Order Summary</h2>
        <div className="space-y-2">
          <div className="flex justify-between text-gray-700">
            <span>Subtotal</span>
            <span>${order.subtotal?.toFixed(2) || '0.00'}</span>
          </div>
          <div className="flex justify-between text-gray-700">
            <span>Tax</span>
            <span>${order.tax?.toFixed(2) || '0.00'}</span>
          </div>
          <div className="flex justify-between text-gray-700">
            <span>Shipping</span>
            <span>{order.shipping === 0 ? 'FREE' : `$${order.shipping?.toFixed(2) || '0.00'}`}</span>
          </div>
          <div className="border-t border-gray-200 pt-2">
            <div className="flex justify-between text-lg font-bold text-gray-900">
              <span>Total</span>
              <span>${order.totalAmount?.toFixed(2) || '0.00'}</span>
            </div>
          </div>
        </div>

        {order.paymentId && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Payment ID: <span className="font-mono">{order.paymentId}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Orders Page
 * Displays order history with pagination and detail view
 * Implements Requirements 8.1, 8.2, 8.3 from design.md
 */
const Orders = () => {
  const { id } = useParams()
  const navigate = useNavigate()

  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [lastKey, setLastKey] = useState(null)

  // If there's an ID in the URL, show detail view
  if (id) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <OrderDetail orderId={id} />
      </div>
    )
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async (append = false) => {
    try {
      if (!append) {
        setLoading(true)
        setError(null)
      } else {
        setLoadingMore(true)
      }

      const params = {
        limit: 10
      }

      if (append && lastKey) {
        params.lastKey = lastKey
      }

      const response = await orderApi.getOrders(params)
      const newOrders = response.orders || response || []

      if (append) {
        setOrders(prev => [...prev, ...newOrders])
      } else {
        setOrders(newOrders)
      }

      setLastKey(response.lastKey)
      setHasMore(!!response.lastKey)

    } catch (err) {
      console.error('Error fetching orders:', err)
      setError('Failed to load orders. Please try again.')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      fetchOrders(true)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-start gap-3">
          <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-red-800 font-semibold mb-1">Error Loading Orders</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => fetchOrders()}
              className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Empty state
  if (orders.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <Package className="h-24 w-24 text-gray-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Orders Yet</h1>
          <p className="text-gray-600 mb-6">Start shopping to see your orders here!</p>
          <Link
            to="/products"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors"
          >
            Browse Products
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Order History</h1>
        <p className="text-gray-600">{orders.length} {orders.length === 1 ? 'order' : 'orders'}</p>
      </div>

      {/* Orders List */}
      <div className="space-y-4">
        {orders.map((order) => {
          const statusDisplay = getStatusDisplay(order.status)
          const StatusIcon = statusDisplay.icon

          return (
            <div
              key={order.orderId}
              onClick={() => navigate(`/orders/${order.orderId}`, { state: { order } })}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">
                    Order #{order.orderId?.slice(0, 8)}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {new Date(order.createdAt || order.timestamp).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${statusDisplay.color}`}>
                    <StatusIcon className="h-4 w-4" />
                    <span className="font-medium text-sm">{statusDisplay.label}</span>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </div>
              </div>

              {/* Order Items Preview */}
              <div className="flex gap-4 mb-4">
                {order.items?.slice(0, 3).map((item, index) => (
                  <img
                    key={index}
                    src={item.imageUrl || 'https://via.placeholder.com/60x60'}
                    alt={item.name}
                    className="w-16 h-16 object-cover rounded-md"
                  />
                ))}
                {order.items?.length > 3 && (
                  <div className="w-16 h-16 bg-gray-100 rounded-md flex items-center justify-center text-gray-600 text-sm font-medium">
                    +{order.items.length - 3}
                  </div>
                )}
              </div>

              {/* Order Total */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {order.items?.length || 0} {order.items?.length === 1 ? 'item' : 'items'}
                </span>
                <span className="font-semibold text-gray-900">
                  Total: ${order.totalAmount?.toFixed(2) || '0.00'}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div className="mt-8 text-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loadingMore ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Loading...
              </span>
            ) : (
              'Load More Orders'
            )}
          </button>
        </div>
      )}
    </div>
  )
}

export default Orders
