import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cartAPI, ordersAPI, paymentAPI } from '../services/api';
import { getCurrentUser } from 'aws-amplify/auth';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';
import { v4 as uuidv4 } from 'uuid';

function Checkout() {
  const [cartItems, setCartItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [user, setUser] = useState(null);
  const [paymentInfo, setPaymentInfo] = useState({
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadCheckoutData();
  }, []);

  const loadCheckoutData = async () => {
    setLoading(true);
    try {
      const [cartData, userData] = await Promise.all([
        cartAPI.get(),
        getCurrentUser(),
      ]);

      setCartItems(Array.isArray(cartData) ? cartData : []);
      setUser(userData);
    } catch (error) {
      console.error('Failed to load checkout data:', error);
      toast.error('Failed to load checkout information');
    } finally {
      setLoading(false);
    }
  };

  const calculateTotal = () => {
    return cartItems.reduce((sum, item) => {
      const price = typeof item.price === 'number' ? item.price : parseFloat(item.price) || 0;
      return sum + price * item.quantity;
    }, 0);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPaymentInfo({ ...paymentInfo, [name]: value });
  };

  const handleSubmitOrder = async (e) => {
    e.preventDefault();
    setProcessing(true);

    try {
      const subtotal = calculateTotal();
      const tax = subtotal * 0.1;
      const total = subtotal + tax;

      // Step 1: Mock payment processing (Stripe)
      toast.loading('Processing payment...');
      const paymentIntent = await paymentAPI.createPaymentIntent(total);

      await new Promise((resolve) => setTimeout(resolve, 1500)); // Simulate processing time

      const paymentConfirmation = await paymentAPI.confirmPayment(
        paymentIntent.paymentIntentId,
        {
          cardNumber: paymentInfo.cardNumber.slice(-4),
          cardName: paymentInfo.cardName,
        }
      );

      if (paymentConfirmation.status !== 'succeeded') {
        throw new Error('Payment failed');
      }

      toast.dismiss();
      toast.success('Payment successful!');

      // Step 2: Create order
      const orderData = {
        orderId: uuidv4(),
        userId: user.userId || user.username,
        items: cartItems.map((item) => ({
          productId: item.productId,
          name: item.name,
          price: typeof item.price === 'number' ? item.price : parseFloat(item.price),
          quantity: item.quantity,
        })),
        totalAmount: total,
        paymentId: paymentIntent.paymentIntentId,
        timestamp: Date.now(),
        email: user.signInDetails?.loginId || user.username,
      };

      await ordersAPI.create(orderData);

      toast.success('Order placed successfully!');

      // Redirect to orders page
      setTimeout(() => {
        navigate('/orders');
      }, 1500);
    } catch (error) {
      console.error('Checkout error:', error);
      toast.dismiss();
      toast.error(error.message || 'Failed to process order');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading checkout..." />;
  }

  if (cartItems.length === 0) {
    return (
      <div className="page-container">
        <div className="text-center py-16">
          <div className="text-6xl mb-4">🛒</div>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Your cart is empty</h2>
          <p className="text-gray-600 mb-8">Add some products before checking out!</p>
          <button onClick={() => navigate('/products')} className="btn-primary">
            Browse Products
          </button>
        </div>
      </div>
    );
  }

  const subtotal = calculateTotal();
  const tax = subtotal * 0.1;
  const total = subtotal + tax;

  return (
    <div className="page-container">
      <h1 className="text-4xl font-bold mb-8 gradient-text">Checkout</h1>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Payment Form */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-2xl font-bold mb-6">Payment Information</h2>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-yellow-800">
                <strong>Demo Mode:</strong> This is a mock payment form. Use any test card details.
                <br />
                Example: 4242 4242 4242 4242, any future date, any CVV.
              </p>
            </div>

            <form onSubmit={handleSubmitOrder}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cardholder Name
                  </label>
                  <input
                    type="text"
                    name="cardName"
                    value={paymentInfo.cardName}
                    onChange={handleInputChange}
                    placeholder="John Doe"
                    className="input-field"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Card Number
                  </label>
                  <input
                    type="text"
                    name="cardNumber"
                    value={paymentInfo.cardNumber}
                    onChange={handleInputChange}
                    placeholder="4242 4242 4242 4242"
                    maxLength={19}
                    className="input-field"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Expiry Date
                    </label>
                    <input
                      type="text"
                      name="expiryDate"
                      value={paymentInfo.expiryDate}
                      onChange={handleInputChange}
                      placeholder="MM/YY"
                      maxLength={5}
                      className="input-field"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      CVV
                    </label>
                    <input
                      type="text"
                      name="cvv"
                      value={paymentInfo.cvv}
                      onChange={handleInputChange}
                      placeholder="123"
                      maxLength={4}
                      className="input-field"
                      required
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={processing}
                className="btn-primary w-full mt-8 text-lg py-3"
              >
                {processing ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : (
                  `Pay $${total.toFixed(2)}`
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="card sticky top-24">
            <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

            <div className="space-y-3 mb-6">
              {cartItems.map((item) => {
                const price = typeof item.price === 'number'
                  ? item.price
                  : parseFloat(item.price) || 0;

                return (
                  <div key={item.productId} className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {item.name} x {item.quantity}
                    </span>
                    <span className="font-medium">
                      ${(price * item.quantity).toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="border-t pt-4 space-y-3">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Shipping</span>
                <span className="text-green-600 font-medium">FREE</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Tax (10%)</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div className="border-t pt-3">
                <div className="flex justify-between text-2xl font-bold">
                  <span>Total</span>
                  <span className="text-blue-600">${total.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Checkout;
