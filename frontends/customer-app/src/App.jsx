import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'

import Layout from './components/Layout'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Cart from './pages/Cart'
import Checkout from './pages/Checkout'
import Orders from './pages/Orders'
import Profile from './pages/Profile'

function App() {
  return (
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
            <Authenticator>
              <Layout />
            </Authenticator>
          }>
            <Route index element={<Cart />} />
          </Route>
          
          <Route path="/checkout" element={
            <Authenticator>
              <Layout />
            </Authenticator>
          }>
            <Route index element={<Checkout />} />
          </Route>
          
          <Route path="/orders" element={
            <Authenticator>
              <Layout />
            </Authenticator>
          }>
            <Route index element={<Orders />} />
          </Route>
          
          <Route path="/profile" element={
            <Authenticator>
              <Layout />
            </Authenticator>
          }>
            <Route index element={<Profile />} />
          </Route>
        </Routes>
      </div>
    </Router>
  )
}

export default App