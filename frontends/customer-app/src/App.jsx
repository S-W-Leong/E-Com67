import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Authenticator, useAuthenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'

import Layout from './components/Layout'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Cart from './pages/Cart'
import Checkout from './pages/Checkout'
import Orders from './pages/Orders'
import Profile from './pages/Profile'

// Protected Route wrapper component
function ProtectedRoute({ children }) {
  const { user } = useAuthenticator((context) => [context.user])

  if (!user) {
    return <Authenticator>{children}</Authenticator>
  }

  return children
}

function App() {
  return (
    <Authenticator.Provider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="products" element={<Products />} />
              <Route path="products/:id" element={<ProductDetail />} />
            </Route>

            {/* Protected routes - require authentication */}
            <Route path="/cart" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Cart />} />
            </Route>

            <Route path="/checkout" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Checkout />} />
            </Route>

            <Route path="/orders" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Orders />} />
              <Route path=":id" element={<Orders />} />
            </Route>

            <Route path="/profile" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Profile />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </Authenticator.Provider>
  )
}

export default App