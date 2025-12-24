import React, { useState } from 'react'
import { useStripe, useElements, PaymentElement } from '@stripe/react-stripe-js'
import { AlertCircle, CreditCard } from 'lucide-react'

/**
 * PaymentForm Component
 * Handles Stripe payment method collection using PaymentElement
 * Integrates with the checkout workflow
 */
const PaymentForm = React.forwardRef(({ onPaymentMethodReady, loading, disabled }, ref) => {
  const stripe = useStripe()
  const elements = useElements()
  const [paymentError, setPaymentError] = useState(null)
  const [paymentReady, setPaymentReady] = useState(false)

  /**
   * Handle payment element ready state
   */
  const handleReady = () => {
    setPaymentReady(true)
    if (onPaymentMethodReady) {
      onPaymentMethodReady(true)
    }
  }

  /**
   * Handle payment element changes
   */
  const handleChange = (event) => {
    if (event.error) {
      setPaymentError(event.error.message)
    } else {
      setPaymentError(null)
    }
  }

  /**
   * Create payment method for checkout
   */
  const createPaymentMethod = async () => {
    if (!stripe || !elements) {
      throw new Error('Stripe has not loaded yet')
    }

    // Validate the payment element
    const { error: submitError } = await elements.submit()
    if (submitError) {
      setPaymentError(submitError.message)
      throw new Error(submitError.message)
    }

    // Create payment method
    const { error, paymentMethod } = await stripe.createPaymentMethod({
      elements,
      params: {
        billing_details: {
          // Billing details will be collected by PaymentElement
        },
      },
    })

    if (error) {
      setPaymentError(error.message)
      throw new Error(error.message)
    }

    return paymentMethod
  }

  // Expose createPaymentMethod to parent component
  React.useImperativeHandle(ref, () => ({
    createPaymentMethod,
  }))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-6">
        <CreditCard className="h-5 w-5 text-gray-600" />
        <h2 className="text-xl font-bold text-gray-900">Payment Information</h2>
      </div>

      <div className="space-y-4">
        {/* Payment Element Container */}
        <div className="payment-element-container">
          <PaymentElement
            onReady={handleReady}
            onChange={handleChange}
            options={{
              layout: {
                type: 'tabs',
                defaultCollapsed: false,
              },
              fields: {
                billingDetails: {
                  address: {
                    country: 'auto',
                  },
                },
              },
              terms: {
                card: 'never',
              },
            }}
          />
        </div>

        {/* Error Display */}
        {paymentError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-800 font-semibold mb-1">Payment Error</h3>
              <p className="text-red-700 text-sm">{paymentError}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-700 text-sm">Processing payment...</p>
          </div>
        )}

        {/* Payment Ready Indicator */}
        {paymentReady && !paymentError && !loading && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-green-700 text-sm">✓ Payment method ready</p>
          </div>
        )}
      </div>
    </div>
  )
})

PaymentForm.displayName = 'PaymentForm'

export default PaymentForm