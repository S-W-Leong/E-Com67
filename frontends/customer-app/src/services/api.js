import { fetchAuthSession } from 'aws-amplify/auth'
import { ApiClient } from '@e-com67/shared'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Function to get current auth token
const getAuthToken = async () => {
  try {
    const session = await fetchAuthSession()
    return session.tokens?.idToken?.toString()
  } catch (error) {
    console.warn('No active session')
    return null
  }
}

// Create API client instance
const apiClient = new ApiClient(API_BASE_URL, getAuthToken)

/**
 * Product API Service
 * Handles all product-related API calls
 */
export const productApi = {
  /**
   * Get all products with optional filtering
   * @param {Object} params - Query parameters
   * @param {string} params.category - Filter by category
   * @param {number} params.limit - Number of items per page
   * @param {string} params.lastKey - Pagination key
   * @returns {Promise<{products: Array, lastKey: string}>}
   */
  async getProducts(params = {}) {
    const queryParams = new URLSearchParams()

    if (params.category) queryParams.append('category', params.category)
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.lastKey) queryParams.append('lastKey', params.lastKey)

    const queryString = queryParams.toString()
    const url = `/products${queryString ? `?${queryString}` : ''}`

    return await apiClient.get(url)
  },

  /**
   * Get a single product by ID
   * @param {string} productId - Product ID
   * @returns {Promise<Object>} Product details
   */
  async getProduct(productId) {
    return await apiClient.get(`/products/${productId}`)
  },

  /**
   * Search products
   * @param {string} query - Search query
   * @param {Object} params - Additional search parameters
   * @returns {Promise<Array>} Search results
   */
  async searchProducts(query, params = {}) {
    const queryParams = new URLSearchParams({ q: query })

    if (params.category) queryParams.append('category', params.category)
    if (params.limit) queryParams.append('limit', params.limit)

    return await apiClient.get(`/search?${queryParams.toString()}`)
  }
}

/**
 * Cart API Service
 * Handles all cart-related API calls
 */
export const cartApi = {
  /**
   * Get current user's cart
   * @returns {Promise<Object>} Cart with items
   */
  async getCart() {
    return await apiClient.get('/cart')
  },

  /**
   * Add item to cart
   * @param {string} productId - Product ID
   * @param {number} quantity - Quantity to add
   * @returns {Promise<Object>} Updated cart
   */
  async addToCart(productId, quantity = 1) {
    return await apiClient.post('/cart', { productId, quantity })
  },

  /**
   * Update cart item quantity
   * @param {string} productId - Product ID
   * @param {number} quantity - New quantity
   * @returns {Promise<Object>} Updated cart
   */
  async updateCartItem(productId, quantity) {
    return await apiClient.post('/cart', { productId, quantity })
  },

  /**
   * Remove item from cart
   * @param {string} productId - Product ID
   * @returns {Promise<Object>} Updated cart
   */
  async removeFromCart(productId) {
    return await apiClient.delete(`/cart?productId=${productId}`)
  },

  /**
   * Clear entire cart
   * @returns {Promise<Object>} Empty cart
   */
  async clearCart() {
    return await apiClient.delete('/cart')
  }
}

/**
 * Order API Service
 * Handles all order-related API calls
 */
export const orderApi = {
  /**
   * Get user's order history
   * @param {Object} params - Query parameters
   * @returns {Promise<Array>} List of orders
   */
  async getOrders(params = {}) {
    const queryParams = new URLSearchParams()

    if (params.limit) queryParams.append('limit', params.limit)
    if (params.lastKey) queryParams.append('lastKey', params.lastKey)

    const queryString = queryParams.toString()
    const url = `/orders${queryString ? `?${queryString}` : ''}`

    return await apiClient.get(url)
  },

  /**
   * Get a single order by ID
   * @param {string} orderId - Order ID
   * @returns {Promise<Object>} Order details
   */
  async getOrder(orderId) {
    return await apiClient.get(`/orders/${orderId}`)
  },

  /**
   * Place a new order
   * @param {Object} orderData - Order data
   * @returns {Promise<Object>} Created order
   */
  async placeOrder(orderData) {
    return await apiClient.post('/orders', orderData)
  }
}

export default {
  product: productApi,
  cart: cartApi,
  order: orderApi
}
