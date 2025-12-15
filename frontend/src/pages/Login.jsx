import { useState } from 'react';
import { signIn, signUp, confirmSignUp } from 'aws-amplify/auth';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

function Login() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [needsConfirmation, setNeedsConfirmation] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignIn = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await signIn({
        username: email,
        password: password,
      });

      toast.success('Login successful!');
      navigate('/products');
    } catch (error) {
      console.error('Sign in error:', error);
      toast.error(error.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await signUp({
        username: email,
        password: password,
        options: {
          userAttributes: {
            email: email,
          },
          autoSignIn: true,
        },
      });

      toast.success('Sign up successful! Please check your email for the confirmation code.');
      setNeedsConfirmation(true);
    } catch (error) {
      console.error('Sign up error:', error);
      toast.error(error.message || 'Failed to sign up');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSignUp = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await confirmSignUp({
        username: email,
        confirmationCode: confirmationCode,
      });

      toast.success('Email confirmed! You can now sign in.');
      setNeedsConfirmation(false);
      setIsSignUp(false);
      setConfirmationCode('');
    } catch (error) {
      console.error('Confirmation error:', error);
      toast.error(error.message || 'Failed to confirm sign up');
    } finally {
      setLoading(false);
    }
  };

  if (needsConfirmation) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
        <div className="bg-white p-8 rounded-lg shadow-2xl w-full max-w-md">
          <h2 className="text-3xl font-bold mb-6 text-center text-gray-900">
            Confirm Your Email
          </h2>
          <p className="text-gray-600 mb-6 text-center">
            We've sent a confirmation code to <strong>{email}</strong>
          </p>

          <form onSubmit={handleConfirmSignUp}>
            <input
              type="text"
              placeholder="Enter confirmation code"
              value={confirmationCode}
              onChange={(e) => setConfirmationCode(e.target.value)}
              className="input-field mb-6"
              required
            />

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Confirming...' : 'Confirm Email'}
            </button>
          </form>

          <button
            onClick={() => {
              setNeedsConfirmation(false);
              setIsSignUp(false);
            }}
            className="w-full mt-4 text-blue-600 hover:underline"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center px-4">
      <div className="bg-white p-8 rounded-lg shadow-2xl w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">🛍️ E-Com67</h1>
          <h2 className="text-2xl font-bold text-gray-900">
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-gray-600 mt-2">
            {isSignUp
              ? 'Sign up to start shopping'
              : 'Sign in to continue shopping'}
          </p>
        </div>

        <form onSubmit={isSignUp ? handleSignUp : handleSignIn}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                placeholder={isSignUp ? 'Minimum 8 characters' : 'Your password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                required
                minLength={8}
              />
            </div>

            {isSignUp && (
              <p className="text-sm text-gray-600">
                Password must be at least 8 characters long
              </p>
            )}
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full mt-6">
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                {isSignUp ? 'Creating Account...' : 'Signing In...'}
              </span>
            ) : (
              <span>{isSignUp ? 'Sign Up' : 'Sign In'}</span>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => {
                setIsSignUp(!isSignUp);
                setEmail('');
                setPassword('');
              }}
              className="text-blue-600 hover:underline font-semibold"
            >
              {isSignUp ? 'Sign In' : 'Sign Up'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
