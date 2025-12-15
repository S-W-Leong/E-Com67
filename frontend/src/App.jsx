import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Amplify } from 'aws-amplify';
import { Hub } from 'aws-amplify/utils';
import { getCurrentUser } from 'aws-amplify/auth';
import { Toaster } from 'react-hot-toast';
import { amplifyConfig } from './config/aws-config';

import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import ChatWidget from './components/ChatWidget';
import LoadingSpinner from './components/LoadingSpinner';

import Login from './pages/Login';
import Products from './pages/Products';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import NotFound from './pages/NotFound';

// Configure Amplify
Amplify.configure(amplifyConfig);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();

    // Listen for auth events (sign in, sign out)
    const hubListener = Hub.listen('auth', ({ payload }) => {
      const { event } = payload;
      console.log('Auth event:', event);

      if (event === 'signedIn' || event === 'autoSignIn') {
        checkUser();
      } else if (event === 'signedOut') {
        setUser(null);
      }
    });

    return () => hubListener();
  }, []);

  const checkUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading application..." />;
  }

  return (
    <ErrorBoundary>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10B981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 4000,
                iconTheme: {
                  primary: '#EF4444',
                  secondary: '#fff',
                },
              },
            }}
          />

          {user && <Navbar user={user} />}

          <Routes>
            {!user ? (
              <>
                <Route path="/login" element={<Login />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </>
            ) : (
              <>
                <Route path="/products" element={<Products />} />
                <Route path="/cart" element={<Cart />} />
                <Route path="/checkout" element={<Checkout />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/" element={<Navigate to="/products" replace />} />
                <Route path="/login" element={<Navigate to="/products" replace />} />
                <Route path="*" element={<NotFound />} />
              </>
            )}
          </Routes>

          {user && <ChatWidget />}
        </div>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
