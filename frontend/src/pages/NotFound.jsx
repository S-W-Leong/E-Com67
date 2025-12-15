import { useNavigate } from 'react-router-dom';

function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-9xl font-bold text-blue-600 mb-4">404</h1>
        <h2 className="text-4xl font-bold text-gray-900 mb-4">Page Not Found</h2>
        <p className="text-gray-600 mb-8 max-w-md">
          Sorry, the page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex gap-4 justify-center">
          <button onClick={() => navigate(-1)} className="btn-secondary">
            Go Back
          </button>
          <button onClick={() => navigate('/products')} className="btn-primary">
            Go to Products
          </button>
        </div>
      </div>
    </div>
  );
}

export default NotFound;
