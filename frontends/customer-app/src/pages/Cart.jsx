import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ShoppingCart, Trash2, Plus, Minus, ArrowLeft, AlertCircle } from 'lucide-react'
import { cartApi } from '../services/api'

/**
 * Cart Page
 * Shopping cart management with item updates and removal
 * Implements Requirements 4.1, 4.2, 4.3, 4.4 from design.md
 */
const Cart = () => {
  const navigate = useNavigate()

  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatingItem, setUpdatingItem] = useState(null)
  const [removingItem, setRemovingItem] = useState(null)

  /**
   * Fetch cart on component mount
   */
  useEffect(() => {
    fetchCart()
  }, [])

  /**
   * Fetch cart from API
   */
  const fetchCart = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await cartApi.getCart()
      setCart(data)
    } catch (err) {
      console.error('Error fetching cart:', err)
      setError(err.response?.data?.error?.message || 'Failed to load cart. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Update item quantity
   */
  const updateQuantity = async (productId, newQuantity) => {
    if (newQuantity < 1) return

    try {
      setUpdatingItem(productId)
      const updatedCart = await cartApi.updateCartItem(productId, newQuantity)
      setCart(updatedCart)
    } catch (err) {
      console.error('Error updating quantity:', err)
      alert('Failed to update quantity. Please try again.')
    } finally {
      setUpdatingItem(null)
    }
  }

  /**
   * Remove item from cart
   */
  const removeItem = async (productId) => {
    if (!confirm('Remove this item from your cart?')) return

    try {
      setRemovingItem(productId)
      const updatedCart = await cartApi.removeFromCart(productId)
      setCart(updatedCart)
    } catch (err) {
      console.error('Error removing item:', err)
      alert('Failed to remove item. Please try again.')
    } finally {
      setRemovingItem(null)
    }
  }

  /**
   * Calculate cart totals
   */
  const calculateTotals = () => {
    if (!cart || !cart.items || cart.items.length === 0) {
      return { subtotal: 0, tax: 0, total: 0 }
    }

    const subtotal = cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
    const tax = subtotal * 0.10 // 10% tax
    const total = subtotal + tax

    return { subtotal, tax, total }
  }

  const { subtotal, tax, total } = calculateTotals()
  const itemCount = cart?.items?.reduce((sum, item) => sum + item.quantity, 0) || 0

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
            <h3 className="text-red-800 font-semibold mb-1">Error Loading Cart</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={fetchCart}
              className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Empty cart state
  if (!cart || !cart.items || cart.items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <ShoppingCart className="h-24 w-24 text-gray-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Your cart is empty</h1>
          <p className="text-gray-600 mb-6">Add some products to get started!</p>
          <Link
            to="/products"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors"
          >
            Continue Shopping
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5" />
          Continue Shopping
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Shopping Cart</h1>
        <p className="text-gray-600 mt-2">{itemCount} {itemCount === 1 ? 'item' : 'items'}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {cart.items.map((item) => (
              <div
                key={item.productId}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
              >
                <div className="flex gap-4">
                  {/* Product Image */}
                  <Link
                    to={`/products/${item.productId}`}
                    className="flex-shrink-0"
                  >
                    <img
                      src={item.imageUrl || 'https://via.placeholder.com/150x150'}
                      alt={item.name}
                      className="w-24 h-24 object-cover rounded-md"
                    />
                  </Link>

                  {/* Product Details */}
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/products/${item.productId}`}
                      className="text-lg font-semibold text-gray-900 hover:text-blue-600 line-clamp-2"
                    >
                      {item.name}
                    </Link>
                    <p className="text-gray-600 mt-1">${item.price.toFixed(2)} each</p>

                    {/* Quantity Controls */}
                    <div className="flex items-center gap-4 mt-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                          disabled={updatingItem === item.productId || item.quantity <= 1}
                          className="p-1 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                        <span className="text-gray-900 font-medium w-12 text-center">
                          {updatingItem === item.productId ? (
                            <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                          ) : (
                            item.quantity
                          )}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                          disabled={updatingItem === item.productId}
                          className="p-1 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>

                      <button
                        onClick={() => removeItem(item.productId)}
                        disabled={removingItem === item.productId}
                        className="text-red-600 hover:text-red-700 flex items-center gap-1 text-sm font-medium disabled:opacity-50"
                      >
                        {removingItem === item.productId ? (
                          <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                        ) : (
                          <>
                            <Trash2 className="h-4 w-4" />
                            Remove
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Item Total */}
                  <div className="text-right">
                    <p className="text-xl font-bold text-gray-900">
                      ${(item.price * item.quantity).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-4">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Order Summary</h2>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal ({itemCount} items)</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Estimated Tax (10%)</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div className="border-t border-gray-200 pt-3">
                <div className="flex justify-between text-lg font-bold text-gray-900">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => navigate('/checkout')}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-semibold"
            >
              Proceed to Checkout
            </button>

            <Link
              to="/products"
              className="block text-center text-blue-600 hover:text-blue-700 mt-4 text-sm font-medium"
            >
              Continue Shopping
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Cart
