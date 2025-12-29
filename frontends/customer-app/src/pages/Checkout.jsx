import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthenticator } from '@aws-amplify/ui-react'
import { AlertCircle, ArrowLeft } from 'lucide-react'
import { loadStripe } from '@stripe/stripe-js'
import { Elements } from '@stripe/react-stripe-js'
import { cartApi, orderApi } from '../services/api'
import { metaPixel } from '../services/metaPixel'
import PaymentForm from '../components/PaymentForm'

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY)

/**
 * Checkout Page
 * Complete checkout flow handled by Step Functions
 * Implements Requirements 5.1, 6.1 from design.md
 */
const Checkout = () => {
  const navigate = useNavigate()
  const { user } = useAuthenticator((context) => [context.user])
  const paymentFormRef = useRef(null)

  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [paymentReady, setPaymentReady] = useState(false)

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

      // Track Meta Pixel InitiateCheckout event
      metaPixel.trackInitiateCheckout(data)
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
   * Handle shipping form submission - now includes payment method creation
   */
  const handleShippingSubmit = async (e) => {
    e.preventDefault()

    if (!validateShipping()) return

    if (!paymentReady) {
      setError('Please complete your payment information')
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Create payment method using the PaymentForm
      let paymentMethod
      try {
        paymentMethod = await paymentFormRef.current?.createPaymentMethod()
        if (!paymentMethod) {
          throw new Error('Failed to create payment method')
        }
      } catch (paymentError) {
        setError(`Payment method error: ${paymentError.message}`)
        return
      }

      // Submit complete checkout data to Step Functions workflow
      const checkoutData = {
        userId: user.userId || user.username,
        shippingAddress: shippingInfo,
        totalAmount: total,
        currency: 'usd',
        paymentMethodId: paymentMethod.id, // Include payment method ID
      }

      console.log('Submitting checkout with payment method:', paymentMethod.id)

      // This triggers the Step Functions checkout workflow
      const result = await orderApi.placeOrder(checkoutData)
      
      // Step Functions returns execution details
      console.log('Checkout workflow started:', result)
      
      // Navigate to success page with execution info
      navigate('/orders', {
        state: { 
          fromCheckout: true, 
          executionArn: result.executionArn,
          paymentMethodId: paymentMethod.id,
          message: 'Your order is being processed. You will receive a confirmation email shortly.'
        }
      })

    } catch (err) {
      console.error('Error starting checkout workflow:', err)
      
      // Handle different types of errors
      if (err.response) {
        // API returned an error response
        const status = err.response.status
        const errorData = err.response.data
        
        if (status === 400) {
          setError('Invalid checkout data. Please check your information and try again.')
        } else if (status === 401) {
          setError('Authentication required. Please log in and try again.')
        } else if (status === 500) {
          setError('Server error occurred. Your order may still be processing. Please check your orders page.')
        } else {
          setError(`Checkout failed: ${errorData?.message || 'Unknown error'}`)
        }
      } else if (err.request) {
        // Network error
        setError('Network error. Please check your connection and try again.')
      } else {
        // Other error
        setError('Failed to process checkout. Please try again.')
      }
    } finally {
      setLoading(false)
    }
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

  // Only render with Stripe Elements if we have a valid cart and total
  const hasValidCart = cart && cart.items && cart.items.length > 0 && total > 0

  // Stripe Elements options - only used when hasValidCart is true
  const stripeOptions = hasValidCart ? {
    mode: 'payment',
    amount: Math.round(total * 100), // Convert to cents
    currency: 'usd',
    paymentMethodCreation: 'manual', // Required for createPaymentMethod
    appearance: {
      theme: 'stripe',
      variables: {
        colorPrimary: '#2563eb', // Blue-600 to match the design
        colorBackground: '#ffffff',
        colorText: '#1f2937', // Gray-800
        colorDanger: '#dc2626', // Red-600
        fontFamily: 'system-ui, sans-serif',
        spacingUnit: '4px',
        borderRadius: '6px',
      },
    },
  } : null

  return (
    <>
      {hasValidCart ? (
        <Elements stripe={stripePromise} options={stripeOptions}>
          <CheckoutContent
            cart={cart}
            loading={loading}
            error={error}
            shippingInfo={shippingInfo}
            setShippingInfo={setShippingInfo}
            shippingErrors={shippingErrors}
            handleShippingSubmit={handleShippingSubmit}
            validateShipping={validateShipping}
            paymentFormRef={paymentFormRef}
            paymentReady={paymentReady}
            setPaymentReady={setPaymentReady}
            navigate={navigate}
            subtotal={subtotal}
            tax={tax}
            shipping={shipping}
            total={total}
            itemCount={itemCount}
            hasValidCart={hasValidCart}
          />
        </Elements>
      ) : (
        <CheckoutContent
          cart={cart}
          loading={loading}
          error={error}
          shippingInfo={shippingInfo}
          setShippingInfo={setShippingInfo}
          shippingErrors={shippingErrors}
          handleShippingSubmit={handleShippingSubmit}
          validateShipping={validateShipping}
          paymentFormRef={paymentFormRef}
          paymentReady={paymentReady}
          setPaymentReady={setPaymentReady}
          navigate={navigate}
          subtotal={subtotal}
          tax={tax}
          shipping={shipping}
          total={total}
          itemCount={itemCount}
          hasValidCart={hasValidCart}
        />
      )}
    </>
  )
}

/**
 * CheckoutContent Component - Separated to use Stripe hooks
 */
const CheckoutContent = ({
  cart,
  loading,
  error,
  shippingInfo,
  setShippingInfo,
  shippingErrors,
  handleShippingSubmit,
  validateShipping,
  paymentFormRef,
  paymentReady,
  setPaymentReady,
  navigate,
  subtotal,
  tax,
  shipping,
  total,
  itemCount,
  hasValidCart,
}) => {
  // Check if we're inside Elements provider
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
          onClick={() => navigate('/cart')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-5 w-5" />
          Back to Cart
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Checkout</h1>
        <p className="text-gray-600 mt-2">Complete your order information below</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Shipping Information Form */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Shipping & Order Information</h2>
            <p className="text-sm text-gray-600 mb-6">
              After submitting this form, your payment will be processed securely and your order will be confirmed.
            </p>

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

              {/* Payment Information Section */}
              {hasValidCart ? (
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <PaymentForm
                    ref={paymentFormRef}
                    onPaymentMethodReady={setPaymentReady}
                    loading={loading}
                  />
                </div>
              ) : (
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-yellow-700 text-sm">
                      Payment information will be available once your cart is loaded.
                    </p>
                  </div>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-red-800 font-semibold mb-1">Error</h3>
                    <p className="text-red-700">{error}</p>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || (hasValidCart && !paymentReady)}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing Order...' : hasValidCart ? `Complete Order - $${total.toFixed(2)}` : 'Loading Cart...'}
              </button>
            </form>
          </div>
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