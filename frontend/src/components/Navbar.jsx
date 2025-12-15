import { Link, useNavigate } from 'react-router-dom';
import { signOut } from 'aws-amplify/auth';
import toast from 'react-hot-toast';

function Navbar({ user }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await signOut();
      toast.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Failed to logout');
    }
  };

  if (!user) return null;

  return (
    <nav className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <Link to="/products" className="text-2xl font-bold hover:opacity-80 transition-opacity">
            🛍️ E-Com67
          </Link>

          <div className="flex gap-6 items-center">
            <Link
              to="/products"
              className="hover:bg-white/10 px-3 py-2 rounded-lg transition-colors"
            >
              Products
            </Link>
            <Link
              to="/cart"
              className="hover:bg-white/10 px-3 py-2 rounded-lg transition-colors"
            >
              Cart
            </Link>
            <Link
              to="/orders"
              className="hover:bg-white/10 px-3 py-2 rounded-lg transition-colors"
            >
              Orders
            </Link>

            <div className="border-l border-white/30 pl-6 flex items-center gap-4">
              <span className="text-sm opacity-90">
                {user?.signInDetails?.loginId || user?.username || 'User'}
              </span>
              <button
                onClick={handleLogout}
                className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg transition-colors font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
