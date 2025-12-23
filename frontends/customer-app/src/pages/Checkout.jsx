import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { Lock, AlertCircle, ArrowLeft, CheckCircle } from 'lucide-react'
import { cartApi, orderApi } from '../services/api'

// Initialize Stripe (publishable key from environment)
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_placeholder')

/**
 * Checkout Form Component
 * Handles payment processing with Stripe Elements
 */
const CheckoutForm = ({ cart, shippingInfo, onSuccess }) => {
  const stripe = useStripe()
  const elements = useElements()
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!stripe || !elements) {
      return
    }

    try {
      setProcessing(true)
      setError(null)

      // Confirm payment with Stripe
      const { error: stripeError, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: 'if_required',
      })

      if (stripeError) {
        setError(stripeError.message)
        setProcessing(false)
        return
      }

      // Create order
      const orderData = {
        paymentIntentId: paymentIntent.id,
        shippingAddress: shippingInfo,
      }

      const order = await orderApi.placeOrder(orderData)

      // Clear cart and redirect to success
      onSuccess(order)

    } catch (err) {
      console.error('Payment error:', err)
      setError(err.response?.data?.error?.message || 'Payment failed. Please try again.')
      setProcessing(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <PaymentElement />

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={!stripe || processing}
        className="w-full bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {processing ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            Processing...
          </>
        ) : (
          <>
            <Lock className="h-5 w-5" />
            Pay ${(cart.total / 100).toFixed(2)}
          </>
        )}
      </button>

      <p className="text-xs text-gray-500 text-center">
        Your payment information is encrypted and secure
      </p>
    </form>
  )
}

/**
 * Checkout Page
 * Complete checkout flow with shipping and payment
 * Implements Requirements 5.1, 6.1 from design.md
 */
const Checkout = () => {
  const navigate = useNavigate()

  const [step, setStep] = useState(1) // 1: Shipping, 2: Payment
  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [clientSecret, setClientSecret] = useState(null)

  const [shippingInfo, setShippingInfo] = useState({
    fullName: '',
    email: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: 'US',
    phone: '',
  })

  const [shippingErrors, setShippingErrors] = useState({})

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

      if (!data || !data.items || data.items.length === 0) {
        navigate('/cart')
        return
      }

      setCart(data)
    } catch (err) {
      console.error('Error fetching cart:', err)
      setError('Failed to load cart. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Validate shipping form
   */
  const validateShipping = () => {
    const errors = {}

    if (!shippingInfo.fullName.trim()) errors.fullName = 'Full name is required'
    if (!shippingInfo.email.trim()) errors.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(shippingInfo.email)) errors.email = 'Email is invalid'
    if (!shippingInfo.address.trim()) errors.address = 'Address is required'
    if (!shippingInfo.city.trim()) errors.city = 'City is required'
    if (!shippingInfo.state.trim()) errors.state = 'State is required'
    if (!shippingInfo.zipCode.trim()) errors.zipCode = 'ZIP code is required'
    if (!shippingInfo.phone.trim()) errors.phone = 'Phone is required'

    setShippingErrors(errors)
    return Object.keys(errors).length === 0
  }

  /**
   * Handle shipping form submission
   */
  const handleShippingSubmit = async (e) => {
    e.preventDefault()

    if (!validateShipping()) return

    try {
      setLoading(true)

      // Create payment intent (mock - in real app, call backend API)
      // const response = await orderApi.createPaymentIntent({ cartTotal: cart.total })
      // setClientSecret(response.clientSecret)

      // For demo purposes, use a placeholder
      setClientSecret('placeholder_client_secret')
      setStep(2)
    } catch (err) {
      console.error('Error creating payment intent:', err)
      setError('Failed to proceed to payment. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  /**
   * Handle successful order placement
   */
  const handleOrderSuccess = (order) => {
    navigate(`/orders/${order.orderId}`, {
      state: { fromCheckout: true, order }
    })
  }

  /**
   * Calculate cart totals
   */
  const calculateTotals = () => {
    if (!cart || !cart.items) return { subtotal: 0, tax: 0, shipping: 0, total: 0 }

    const subtotal = cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
    const tax = subtotal * 0.10
    const shipping = subtotal > 50 ? 0 : 9.99
    const total = subtotal + tax + shipping

    return { subtotal, tax, shipping, total }
  }

  const { subtotal, tax, shipping, total } = calculateTotals()
  const itemCount = cart?.items?.reduce((sum, item) => sum + item.quantity, 0) || 0

  // Loading state
  if (loading && !cart) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  // Error state
  if (error && !cart) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-start gap-3">
          <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-red-800 font-semibold mb-1">Error</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => navigate('/cart')}
              className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Return to Cart
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => step === 1 ? navigate('/cart') : setStep(1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5" />
          {step === 1 ? 'Back to Cart' : 'Back to Shipping'}
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Checkout</h1>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-4">
          <div className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'
            }`}>
              {step > 1 ? <CheckCircle className="h-5 w-5" /> : '1'}
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">Shipping</span>
          </div>
          <div className="w-16 h-0.5 bg-gray-300"></div>
          <div className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'
            }`}>
              2
            </div>
            <span className="ml-2 text-sm font-medium text-gray-900">Payment</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {step === 1 ? (
            /* Shipping Information Form */
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Shipping Information</h2>

              <form onSubmit={handleShippingSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={shippingInfo.fullName}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, fullName: e.target.value })}
                      className={`w-full border ${shippingErrors.fullName ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.fullName && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.fullName}</p>
                    )}
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email *
                    </label>
                    <input
                      type="email"
                      value={shippingInfo.email}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, email: e.target.value })}
                      className={`w-full border ${shippingErrors.email ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.email && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.email}</p>
                    )}
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Address *
                    </label>
                    <input
                      type="text"
                      value={shippingInfo.address}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, address: e.target.value })}
                      className={`w-full border ${shippingErrors.address ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.address && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.address}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      City *
                    </label>
                    <input
                      type="text"
                      value={shippingInfo.city}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, city: e.target.value })}
                      className={`w-full border ${shippingErrors.city ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.city && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.city}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      State *
                    </label>
                    <input
                      type="text"
                      value={shippingInfo.state}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, state: e.target.value })}
                      className={`w-full border ${shippingErrors.state ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.state && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.state}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ZIP Code *
                    </label>
                    <input
                      type="text"
                      value={shippingInfo.zipCode}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, zipCode: e.target.value })}
                      className={`w-full border ${shippingErrors.zipCode ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.zipCode && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.zipCode}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone *
                    </label>
                    <input
                      type="tel"
                      value={shippingInfo.phone}
                      onChange={(e) => setShippingInfo({ ...shippingInfo, phone: e.target.value })}
                      className={`w-full border ${shippingErrors.phone ? 'border-red-300' : 'border-gray-300'} rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    />
                    {shippingErrors.phone && (
                      <p className="text-sm text-red-600 mt-1">{shippingErrors.phone}</p>
                    )}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {loading ? 'Processing...' : 'Continue to Payment'}
                </button>
              </form>
            </div>
          ) : (
            /* Payment Form */
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Payment Information</h2>

              {clientSecret && stripePromise ? (
                <Elements
                  stripe={stripePromise}
                  options={{
                    clientSecret,
                    appearance: {
                      theme: 'stripe',
                    },
                  }}
                >
                  <CheckoutForm
                    cart={{ total: Math.round(total * 100) }}
                    shippingInfo={shippingInfo}
                    onSuccess={handleOrderSuccess}
                  />
                </Elements>
              ) : (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-gray-600 mt-4">Loading payment form...</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-4">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Order Summary</h2>

            {/* Cart Items */}
            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
              {cart?.items?.map((item) => (
                <div key={item.productId} className="flex gap-3">
                  <img
                    src={item.imageUrl || 'https://via.placeholder.com/60x60'}
                    alt={item.name}
                    className="w-16 h-16 object-cover rounded-md"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 line-clamp-2">
                      {item.name}
                    </p>
                    <p className="text-sm text-gray-600">
                      Qty: {item.quantity} × ${item.price.toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Totals */}
            <div className="border-t border-gray-200 pt-4 space-y-2">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal ({itemCount} items)</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Shipping</span>
                <span>{shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Tax (10%)</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div className="border-t border-gray-200 pt-2">
                <div className="flex justify-between text-lg font-bold text-gray-900">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {shipping === 0 && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-md p-3">
                <p className="text-sm text-green-800">
                  You qualify for free shipping!
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Checkout
