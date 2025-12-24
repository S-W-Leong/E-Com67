import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useAuthenticator } from '@aws-amplify/ui-react'
import { cartApi } from '../services/api'

/**
 * Cart Context
 * Provides global cart state management across the application.
 * This allows components like the nav bar to display accurate cart item counts.
 */
const CartContext = createContext(null)

/**
 * CartProvider component
 * Wraps the application to provide cart state to all child components.
 */
export function CartProvider({ children }) {
  const { user } = useAuthenticator((context) => [context.user])

  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  /**
   * Calculate total item count in cart
   * Sums the quantity of all items
   */
  const itemCount = cart?.items?.reduce((sum, item) => sum + item.quantity, 0) || 0

  /**
   * Fetch cart from API
   * Only fetches when user is authenticated
   */
  const fetchCart = useCallback(async () => {
    if (!user) {
      setCart(null)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await cartApi.getCart()
      setCart(data)
    } catch (err) {
      console.error('Error fetching cart:', err)
      setError(err.response?.data?.error?.message || 'Failed to load cart')
    } finally {
      setLoading(false)
    }
  }, [user])

  /**
   * Add item to cart and update state
   */
  const addToCart = useCallback(async (productId, quantity = 1) => {
    try {
      const updatedCart = await cartApi.addToCart(productId, quantity)
      setCart(updatedCart)
      return updatedCart
    } catch (err) {
      console.error('Error adding to cart:', err)
      throw err
    }
  }, [])

  /**
   * Update cart item quantity
   */
  const updateCartItem = useCallback(async (productId, quantity) => {
    try {
      const updatedCart = await cartApi.updateCartItem(productId, quantity)
      setCart(updatedCart)
      return updatedCart
    } catch (err) {
      console.error('Error updating cart item:', err)
      throw err
    }
  }, [])

  /**
   * Remove item from cart
   */
  const removeFromCart = useCallback(async (productId) => {
    try {
      const updatedCart = await cartApi.removeFromCart(productId)
      setCart(updatedCart)
      return updatedCart
    } catch (err) {
      console.error('Error removing from cart:', err)
      throw err
    }
  }, [])

  /**
   * Clear entire cart
   */
  const clearCart = useCallback(async () => {
    try {
      const updatedCart = await cartApi.clearCart()
      setCart(updatedCart)
      return updatedCart
    } catch (err) {
      console.error('Error clearing cart:', err)
      throw err
    }
  }, [])

  // Fetch cart when user changes (login/logout)
  useEffect(() => {
    fetchCart()
  }, [fetchCart])

  const value = {
    cart,
    setCart,
    loading,
    error,
    itemCount,
    fetchCart,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart
  }

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  )
}

/**
 * Hook to access cart context
 * Must be used within a CartProvider
 */
export function useCart() {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error('useCart must be used within a CartProvider')
  }
  return context
}

export default CartContext
