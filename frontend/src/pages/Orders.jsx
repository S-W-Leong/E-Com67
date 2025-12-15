import { useState, useEffect } from 'react';
import { ordersAPI } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';

function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await ordersAPI.getAll();
      setOrders(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load orders:', error);
      toast.error('Failed to load orders');
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status) => {
    const colors = {
      PROCESSING: 'bg-yellow-100 text-yellow-800',
      COMPLETED: 'bg-green-100 text-green-800',
      CANCELLED: 'bg-red-100 text-red-800',
      SHIPPED: 'bg-blue-100 text-blue-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <LoadingSpinner message="Loading your orders..." />;
  }

  return (
    <div className="page-container">
      <h1 className="text-4xl font-bold mb-8 gradient-text">Order History</h1>

      {orders.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📦</div>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">No orders yet</h2>
          <p className="text-gray-600 mb-8">
            Start shopping to see your orders here!
          </p>
          <button
            onClick={() => (window.location.href = '/products')}
            className="btn-primary"
          >
            Browse Products
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map((order) => {
            const total = typeof order.totalAmount === 'number'
              ? order.totalAmount
              : parseFloat(order.totalAmount) || 0;

            return (
              <div key={order.orderId} className="card">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">
                      Order #{order.orderId.slice(0, 8)}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {formatDate(order.timestamp)}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                      order.status
                    )}`}
                  >
                    {order.status || 'PROCESSING'}
                  </span>
                </div>

                <div className="border-t border-b py-4 my-4">
                  <div className="space-y-2">
                    {order.items && order.items.length > 0 ? (
                      order.items.map((item, index) => (
                        <div
                          key={index}
                          className="flex justify-between text-sm"
                        >
                          <span className="text-gray-700">
                            {item.name} x {item.quantity}
                          </span>
                          <span className="font-medium">
                            ${((item.price || 0) * (item.quantity || 1)).toFixed(2)}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">No items</p>
                    )}
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-600">Total Amount</p>
                    <p className="text-2xl font-bold text-blue-600">
                      ${total.toFixed(2)}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedOrder(order)}
                    className="btn-secondary"
                  >
                    View Details
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Order Details Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-center">
              <h2 className="text-2xl font-bold">Order Details</h2>
              <button
                onClick={() => setSelectedOrder(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Order Information</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Order ID</p>
                    <p className="font-medium">{selectedOrder.orderId}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Order Date</p>
                    <p className="font-medium">{formatDate(selectedOrder.timestamp)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Status</p>
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        selectedOrder.status
                      )}`}
                    >
                      {selectedOrder.status || 'PROCESSING'}
                    </span>
                  </div>
                  <div>
                    <p className="text-gray-600">Payment ID</p>
                    <p className="font-medium text-xs">{selectedOrder.paymentId}</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Items</h3>
                <div className="space-y-2">
                  {selectedOrder.items && selectedOrder.items.map((item, index) => (
                    <div
                      key={index}
                      className="flex justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{item.name}</p>
                        <p className="text-sm text-gray-600">
                          ${(item.price || 0).toFixed(2)} x {item.quantity}
                        </p>
                      </div>
                      <p className="font-bold">
                        ${((item.price || 0) * (item.quantity || 1)).toFixed(2)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between text-lg font-bold">
                  <span>Total Amount</span>
                  <span className="text-blue-600">
                    ${(typeof selectedOrder.totalAmount === 'number'
                      ? selectedOrder.totalAmount
                      : parseFloat(selectedOrder.totalAmount) || 0
                    ).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Orders;
