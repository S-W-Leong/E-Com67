import { useState } from 'react';
import { cartAPI } from '../services/api';
import toast from 'react-hot-toast';

function ProductCard({ product }) {
  const [loading, setLoading] = useState(false);

  const handleAddToCart = async () => {
    setLoading(true);
    try {
      await cartAPI.add(product.productId, 1);
      toast.success(`${product.name} added to cart!`);
    } catch (error) {
      console.error('Error adding to cart:', error);
      toast.error(error.message || 'Failed to add to cart');
    } finally {
      setLoading(false);
    }
  };

  const price = typeof product.price === 'number'
    ? product.price
    : parseFloat(product.price) || 0;

  return (
    <div className="card group">
      <div className="relative overflow-hidden rounded-lg mb-4 bg-gray-100 h-48">
        {product.imageUrl ? (
          <img
            src={product.imageUrl}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <svg
              className="w-20 h-20"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}
        {product.stock <= 0 && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <span className="bg-red-500 text-white px-4 py-2 rounded-lg font-bold">
              Out of Stock
            </span>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-bold text-gray-900 line-clamp-2">
          {product.name}
        </h3>

        <p className="text-sm text-gray-600 line-clamp-2">
          {product.description || 'No description available'}
        </p>

        <div className="flex items-center justify-between pt-2">
          <span className="text-2xl font-bold text-blue-600">
            ${price.toFixed(2)}
          </span>
          <span className="text-sm text-gray-500">
            {product.category || 'Uncategorized'}
          </span>
        </div>

        {product.stock > 0 && product.stock <= 10 && (
          <p className="text-sm text-orange-600">
            Only {product.stock} left in stock!
          </p>
        )}

        <button
          onClick={handleAddToCart}
          disabled={loading || product.stock <= 0}
          className="btn-primary w-full mt-4"
        >
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
              Adding...
            </span>
          ) : (
            'Add to Cart'
          )}
        </button>
      </div>
    </div>
  );
}

export default ProductCard;
