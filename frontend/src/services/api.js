import axios from 'axios'
import { fetchAuthSession } from 'aws-amplify/auth'

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_ENDPOINT || 'https://placeholder.execute-api.ap-southeast-1.amazonaws.com/prod',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    try {
      const session = await fetchAuthSession()
      const token = session.tokens?.idToken?.toString()
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (error) {
      console.warn('Failed to get auth token:', error)
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could redirect to login
      console.error('Unauthorized access')
    }
    
    return Promise.reject(error)
  }
)

// Product API functions
export const productAPI = {
  // Get all products with optional filtering
  getProducts: async (params = {}) => {
    const response = await api.get('/products', { params })
    return response.data
  },

  // Get single product by ID
  getProduct: async (id) => {
    const response = await api.get(`/products/${id}`)
    return response.data
  },

  // Create new product
  createProduct: async (productData) => {
    const response = await api.post('/products', productData)
    return response.data
  },

  // Update existing product
  updateProduct: async (id, productData) => {
    const response = await api.put(`/products/${id}`, productData)
    return response.data
  },

  // Delete product
  deleteProduct: async (id) => {
    const response = await api.delete(`/products/${id}`)
    return response.data
  },

  // Get admin-specific product data
  getAdminProducts: async (params = {}) => {
    const response = await api.get('/admin/products', { params })
    return response.data
  }
}

// Order API functions
export const orderAPI = {
  // Get all orders (admin view)
  getOrders: async (params = {}) => {
    const response = await api.get('/admin/orders', { params })
    return response.data
  },

  // Get single order details
  getOrder: async (id) => {
    const response = await api.get(`/orders/${id}`)
    return response.data
  },

  // Update order status
  updateOrderStatus: async (id, status) => {
    const response = await api.put(`/admin/orders/${id}`, { status })
    return response.data
  },

  // Search orders with filters
  searchOrders: async (filters = {}) => {
    const response = await api.get('/admin/orders', { params: filters })
    return response.data
  }
}

// Analytics API functions (placeholder for future implementation)
export const analyticsAPI = {
  // Get dashboard metrics
  getDashboardMetrics: async () => {
    // This would be implemented when analytics endpoints are available
    // For now, return mock data
    return {
      totalProducts: 0,
      totalOrders: 0,
      totalRevenue: 0,
      recentOrders: []
    }
  },

  // Get product analytics
  getProductAnalytics: async () => {
    return {
      topProducts: [],
      categoryBreakdown: [],
      inventoryAlerts: []
    }
  }
}

// Search API functions
export const searchAPI = {
  // Search products
  searchProducts: async (query, filters = {}) => {
    const params = { q: query, ...filters }
    const response = await api.get('/search', { params })
    return response.data
  }
}

export default api