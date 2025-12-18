# Stripe Frontend Integration Guide

This guide explains how to integrate the payment system with your frontend application.

## Table of Contents
1. [Current Testing Setup](#current-testing-setup)
2. [Frontend Integration](#frontend-integration)
3. [Testing with Frontend](#testing-with-frontend)
4. [Security Best Practices](#security-best-practices)

---

## Current Testing Setup

### Backend Testing (No Frontend)

For **Step Functions testing** and **backend-only testing**, the Lambda automatically uses Stripe's test payment method:

```python
# payment.py automatically uses pm_card_visa when no paymentMethodId provided
payment_intent = stripe.PaymentIntent.create(
    amount=amount_cents,
    currency=currency,
    payment_method='pm_card_visa',  # Built-in test payment method
    confirm=True,
    off_session=True,
)
```

**Test:**
```bash
python3 tests/test_checkout_integration.py
```

---

## Frontend Integration

### Step 1: Install Stripe.js in Your Frontend

**React/Next.js:**
```bash
npm install @stripe/stripe-js @stripe/react-stripe-js
```

**HTML/Vanilla JS:**
```html
<script src="https://js.stripe.com/v3/"></script>
```

### Step 2: Initialize Stripe with Your Publishable Key

**React Component:**
```jsx
// src/components/CheckoutForm.jsx
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

// Load Stripe (use your publishable key from .env)
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY);

function CheckoutForm() {
  const stripe = useStripe();
  const elements = useElements();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    // Get the card element
    const cardElement = elements.getElement(CardElement);

    // Create payment method from card details
    const {error, paymentMethod} = await stripe.createPaymentMethod({
      type: 'card',
      card: cardElement,
    });

    if (error) {
      console.error('[PaymentMethod Error]', error);
      return;
    }

    // Send payment method ID to your backend
    const response = await fetch('https://your-api-gateway-url/checkout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`,
      },
      body: JSON.stringify({
        paymentMethodId: paymentMethod.id,  // ← Send this to Lambda
        userId: currentUser.id,
        items: cartItems,
        returnUrl: window.location.origin + '/order-confirmation',
      }),
    });

    const result = await response.json();

    if (result.success) {
      // Redirect to order confirmation
      window.location.href = '/order-confirmation';
    } else {
      // Handle error
      console.error('Payment failed:', result.error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <CardElement />
      <button type="submit" disabled={!stripe}>
        Pay Now
      </button>
    </form>
  );
}

// Wrap with Elements provider
export default function CheckoutPage() {
  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm />
    </Elements>
  );
}
```

**Vanilla JS:**
```html
<!-- checkout.html -->
<!DOCTYPE html>
<html>
<head>
  <script src="https://js.stripe.com/v3/"></script>
</head>
<body>
  <form id="payment-form">
    <div id="card-element"></div>
    <button id="submit-button">Pay Now</button>
    <div id="error-message"></div>
  </form>

  <script>
    // Initialize Stripe
    const stripe = Stripe('pk_test_YOUR_PUBLISHABLE_KEY');
    const elements = stripe.elements();
    const cardElement = elements.create('card');
    cardElement.mount('#card-element');

    // Handle form submission
    const form = document.getElementById('payment-form');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      // Create payment method
      const {error, paymentMethod} = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (error) {
        document.getElementById('error-message').textContent = error.message;
        return;
      }

      // Send to your backend
      const response = await fetch('https://your-api-gateway-url/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + userToken,
        },
        body: JSON.stringify({
          paymentMethodId: paymentMethod.id,
          userId: currentUser.id,
          items: cartItems,
          returnUrl: window.location.origin + '/order-confirmation',
        }),
      });

      const result = await response.json();

      if (result.success) {
        window.location.href = '/order-confirmation';
      } else {
        document.getElementById('error-message').textContent = result.error;
      }
    });
  </script>
</body>
</html>
```

### Step 3: Backend Receives Payment Method ID

The Lambda function already handles this! When `paymentMethodId` is provided:

```python
# payment.py (already implemented)
payment_method_id = payment_data.get('paymentMethodId')

if payment_method_id:
    # Frontend provided payment method - use it!
    payment_intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        payment_method=payment_method_id,  # ← From frontend
        confirm=True,
    )
```

---

## Testing with Frontend

### Option 1: Stripe Test Cards (Recommended)

When testing your frontend, use these test card numbers:

| Card Number | Brand | Scenario |
|-------------|-------|----------|
| `4242 4242 4242 4242` | Visa | ✅ Payment succeeds |
| `4000 0025 0000 3155` | Visa | ✅ Requires 3D Secure authentication |
| `4000 0000 0000 9995` | Visa | ❌ Payment declined (insufficient funds) |
| `4000 0000 0000 0002` | Visa | ❌ Payment declined (generic) |
| `5555 5555 5555 4444` | Mastercard | ✅ Payment succeeds |
| `3782 822463 10005` | Amex | ✅ Payment succeeds |

**Any future expiry date works**: `12/25`, `01/30`, etc.
**Any CVC works**: `123`, `456`, etc.

### Option 2: Stripe Testing Dashboard

Visit: https://dashboard.stripe.com/test/payments

You'll see all test payments made from your frontend in real-time!

---

## Security Best Practices

### ✅ DO

1. **Use Stripe.js** to create payment methods client-side
   ```javascript
   const {paymentMethod} = await stripe.createPaymentMethod({...});
   ```

2. **Send only the Payment Method ID** to your backend
   ```javascript
   body: JSON.stringify({ paymentMethodId: paymentMethod.id })
   ```

3. **Use environment variables** for keys
   ```bash
   # Frontend .env
   REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_...

   # Backend (AWS Secrets Manager)
   STRIPE_SECRET_KEY=sk_test_...
   ```

4. **Validate amounts server-side**
   ```python
   # Never trust frontend amounts!
   cart = get_cart_contents(user_id)
   total = calculate_total(cart)  # Calculate on backend
   ```

### ❌ DON'T

1. **Never send raw card numbers** to your backend
   ```javascript
   // ❌ NEVER DO THIS
   body: JSON.stringify({
     cardNumber: '4242424242424242',
     cvv: '123'
   })
   ```

2. **Never expose secret keys** in frontend code
   ```javascript
   // ❌ NEVER DO THIS
   const stripe = Stripe('sk_test_...');  // Secret key in frontend!
   ```

3. **Never trust frontend amounts**
   ```python
   # ❌ NEVER DO THIS
   amount = payment_data['totalAmount']  # From frontend

   # ✅ DO THIS
   cart = get_cart_contents(user_id)
   amount = calculate_total(cart)  # Calculate on backend
   ```

---

## Complete Flow Diagram

```
┌─────────────┐
│  Frontend   │
│   (React)   │
└──────┬──────┘
       │
       │ 1. User enters card details
       │
       ▼
┌─────────────────────┐
│   Stripe.js         │
│   (Client-side)     │
└──────┬──────────────┘
       │
       │ 2. Creates PaymentMethod
       │    Returns: pm_1234abcd
       │
       ▼
┌─────────────────────┐
│   Your Frontend     │
│   API Call          │
└──────┬──────────────┘
       │
       │ 3. POST /checkout
       │    { paymentMethodId: "pm_1234abcd" }
       │
       ▼
┌─────────────────────┐
│   API Gateway       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Payment Lambda    │
│   (Backend)         │
└──────┬──────────────┘
       │
       │ 4. Creates PaymentIntent with payment method
       │    stripe.PaymentIntent.create(payment_method=pm_1234abcd)
       │
       ▼
┌─────────────────────┐
│   Stripe API        │
│   (External)        │
└──────┬──────────────┘
       │
       │ 5. Processes payment
       │    Returns: pi_5678efgh (succeeded)
       │
       ▼
┌─────────────────────┐
│   Step Functions    │
│   Workflow          │
└──────┬──────────────┘
       │
       │ 6. Continues checkout flow
       │    - Update inventory
       │    - Clear cart
       │    - Send confirmation
       │
       ▼
┌─────────────────────┐
│   Order Complete!   │
└─────────────────────┘
```

---

## Environment Setup

### Development (.env)
```bash
# Frontend
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_51...  # Safe to expose

# Backend (AWS Secrets Manager)
STRIPE_SECRET_KEY=sk_test_51...  # NEVER expose
```

### Production
```bash
# Frontend
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_live_51...

# Backend (AWS Secrets Manager)
STRIPE_SECRET_KEY=sk_live_51...
```

---

## Troubleshooting

### "Payment method not found"
- Make sure you're using the correct Stripe key (test with test, live with live)
- Check that `paymentMethod.id` is being sent correctly

### "Amount mismatch"
- Always calculate amounts server-side
- Use cents for amounts: `$10.00 = 1000 cents`

### "3D Secure required"
- Use Stripe's `handleCardAction()` for 3DS
- See: https://stripe.com/docs/payments/3d-secure

---

## Next Steps

1. ✅ **Current**: Backend testing works with `pm_card_visa`
2. 🔨 **Next**: Build frontend checkout form
3. 🧪 **Then**: Test with Stripe test cards
4. 🚀 **Finally**: Switch to live keys for production

Need help? Check out:
- [Stripe React Docs](https://stripe.com/docs/stripe-js/react)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Payment Intents API](https://stripe.com/docs/api/payment_intents)
