import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { apiConfig } from '../config/aws-config';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: apiConfig.endpoint,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error fetching auth session:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const errorMessage = error.response.data?.error || error.response.data?.message || 'An error occurred';
      console.error('API Error:', errorMessage);
      throw new Error(errorMessage);
    } else if (error.request) {
      // Request made but no response received
      console.error('Network Error:', error.message);
      throw new Error('Network error. Please check your connection.');
    } else {
      // Something else happened
      console.error('Error:', error.message);
      throw error;
    }
  }
);

// Products API
export const productsAPI = {
  getAll: async (category = null) => {
    const params = category ? { category } : {};
    const response = await apiClient.get('/products', { params });
    return response.data;
  },

  getById: async (productId) => {
    const response = await apiClient.get(`/products/${productId}`);
    return response.data;
  },

  create: async (productData) => {
    const response = await apiClient.post('/products', productData);
    return response.data;
  },

  update: async (productId, productData) => {
    const response = await apiClient.put(`/products/${productId}`, productData);
    return response.data;
  },

  delete: async (productId) => {
    const response = await apiClient.delete(`/products/${productId}`);
    return response.data;
  },

  search: async (query) => {
    const response = await apiClient.get('/search', { params: { q: query } });
    return response.data;
  },
};

// Cart API
export const cartAPI = {
  get: async () => {
    const response = await apiClient.get('/cart');
    return response.data;
  },

  add: async (productId, quantity = 1) => {
    const response = await apiClient.post('/cart', { productId, quantity });
    return response.data;
  },

  update: async (productId, quantity) => {
    const response = await apiClient.post('/cart', { productId, quantity });
    return response.data;
  },

  remove: async (productId) => {
    const response = await apiClient.delete('/cart', { data: { productId } });
    return response.data;
  },

  clear: async () => {
    const response = await apiClient.delete('/cart/clear');
    return response.data;
  },
};

// Orders API
export const ordersAPI = {
  getAll: async () => {
    const response = await apiClient.get('/orders');
    return response.data;
  },

  getById: async (orderId) => {
    const response = await apiClient.get(`/orders/${orderId}`);
    return response.data;
  },

  create: async (orderData) => {
    const response = await apiClient.post('/orders', orderData);
    return response.data;
  },
};

// Payment API (Mock Stripe for now)
export const paymentAPI = {
  createPaymentIntent: async (amount) => {
    // Mock implementation - replace with actual API call when Stripe is integrated
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          clientSecret: 'mock_client_secret_' + Math.random().toString(36).substring(7),
          paymentIntentId: 'pi_mock_' + Math.random().toString(36).substring(7),
        });
      }, 1000);
    });
  },

  confirmPayment: async (paymentIntentId, paymentMethod) => {
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          status: 'succeeded',
          paymentIntentId,
          paymentMethod,
        });
      }, 1500);
    });
  },
};

export default apiClient;
