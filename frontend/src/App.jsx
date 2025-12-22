import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Orders from './pages/Orders'
import ProductForm from './pages/ProductForm'

function App() {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <Layout user={user} signOut={signOut}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/new" element={<ProductForm />} />
            <Route path="/products/edit/:id" element={<ProductForm />} />
            <Route path="/orders" element={<Orders />} />
          </Routes>
        </Layout>
      )}
    </Authenticator>
  )
}

export default App