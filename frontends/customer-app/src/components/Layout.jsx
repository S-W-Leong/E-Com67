import React from 'react'
import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthenticator } from '@aws-amplify/ui-react'
import { ShoppingCart, User, Search, Menu, X } from 'lucide-react'
import { useState } from 'react'
import ChatWidget from './ChatWidget'
import { useCart } from '../context/CartContext'

const Layout = () => {
  const { user, signOut } = useAuthenticator((context) => [context.user])
  const navigate = useNavigate()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const { itemCount } = useCart()

  const handleSignOut = () => {
    signOut()
    navigate('/')
  }

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Products', href: '/products' },
  ]

  const userNavigation = user ? [
    { name: 'Cart', href: '/cart', icon: ShoppingCart },
    { name: 'Orders', href: '/orders' },
    { name: 'Profile', href: '/profile' },
  ] : []

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <Link to="/" className="text-2xl font-bold text-blue-600">
                E-Com67
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex space-x-8">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors"
                >
                  {item.name}
                </Link>
              ))}
            </nav>

            {/* Search Bar */}
            <div className="hidden md:flex flex-1 max-w-md mx-8">
              <div className="relative w-full">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search products..."
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* User Menu */}
            <div className="flex items-center space-x-4">
              {user ? (
                <>
                  {/* Cart Icon */}
                  <Link
                    to="/cart"
                    className="text-gray-700 hover:text-blue-600 p-2 transition-colors relative"
                  >
                    <ShoppingCart className="h-6 w-6" />
                    {/* Cart badge - shows item count from cart context */}
                    {itemCount > 0 && (
                      <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                        {itemCount > 99 ? '99+' : itemCount}
                      </span>
                    )}
                  </Link>

                  {/* User Menu */}
                  <div className="relative">
                    <button className="flex items-center text-gray-700 hover:text-blue-600 p-2 transition-colors">
                      <User className="h-6 w-6" />
                      <span className="ml-2 text-sm font-medium hidden md:block">
                        {user.signInDetails?.loginId || 'Account'}
                      </span>
                    </button>
                    {/* Dropdown menu would go here */}
                  </div>

                  <button
                    onClick={handleSignOut}
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <div className="flex items-center space-x-4">
                  <Link
                    to="/cart"
                    className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition-colors"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/cart"
                    className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    Sign Up
                  </Link>
                </div>
              )}

              {/* Mobile menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2 text-gray-700 hover:text-blue-600 transition-colors"
              >
                {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {isMobileMenuOpen && (
            <div className="md:hidden border-t border-gray-200 py-4">
              <div className="space-y-2">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="block px-3 py-2 text-gray-700 hover:text-blue-600 transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {item.name}
                  </Link>
                ))}
                
                {/* Mobile Search */}
                <div className="px-3 py-2">
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="text"
                      placeholder="Search products..."
                      className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {user && userNavigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="block px-3 py-2 text-gray-700 hover:text-blue-600 transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">E-Com67</h3>
              <p className="text-gray-600 text-sm">
                Your trusted e-commerce platform for quality products and exceptional service.
              </p>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Shop</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><Link to="/products" className="hover:text-blue-600 transition-colors">All Products</Link></li>
                <li><Link to="/products?category=electronics" className="hover:text-blue-600 transition-colors">Electronics</Link></li>
                <li><Link to="/products?category=clothing" className="hover:text-blue-600 transition-colors">Clothing</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Account</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><Link to="/profile" className="hover:text-blue-600 transition-colors">My Profile</Link></li>
                <li><Link to="/orders" className="hover:text-blue-600 transition-colors">Order History</Link></li>
                <li><Link to="/cart" className="hover:text-blue-600 transition-colors">Shopping Cart</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Support</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li><a href="#" className="hover:text-blue-600 transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-blue-600 transition-colors">Contact Us</a></li>
                <li><a href="#" className="hover:text-blue-600 transition-colors">Shipping Info</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-200 mt-8 pt-8 text-center text-sm text-gray-600">
            <p>&copy; 2024 E-Com67. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* AI Chat Widget */}
      <ChatWidget />
    </div>
  )
}

export default Layout