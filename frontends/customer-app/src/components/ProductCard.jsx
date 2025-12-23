import React from 'react'
import { Link } from 'react-router-dom'
import { Star, ShoppingCart } from 'lucide-react'

/**
 * ProductCard Component
 * Displays a product in either grid or list view
 *
 * @param {Object} product - Product data
 * @param {string} viewMode - 'grid' or 'list'
 * @param {Function} onAddToCart - Callback when add to cart is clicked
 */
const ProductCard = ({ product, viewMode = 'grid', onAddToCart }) => {
  const handleAddToCart = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (onAddToCart) {
      onAddToCart(product)
    }
  }

  const renderStars = (rating) => {
    return [...Array(5)].map((_, i) => (
      <Star
        key={i}
        className={`h-4 w-4 ${
          i < Math.floor(rating)
            ? 'text-yellow-400 fill-current'
            : 'text-gray-300'
        }`}
      />
    ))
  }

  const isOutOfStock = product.stock === 0

  return (
    <Link
      to={`/products/${product.productId}`}
      className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow ${
        viewMode === 'list' ? 'flex' : ''
      } ${isOutOfStock ? 'opacity-60' : ''}`}
    >
      {/* Product Image */}
      <div className={`relative ${viewMode === 'list' ? 'w-48 flex-shrink-0' : 'w-full'}`}>
        <img
          src={product.imageUrl || 'https://via.placeholder.com/300x300?text=No+Image'}
          alt={product.name}
          className={`object-cover ${viewMode === 'list' ? 'h-48' : 'h-64 w-full'}`}
        />
        {isOutOfStock && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <span className="bg-red-600 text-white px-4 py-2 rounded-md font-semibold">
              Out of Stock
            </span>
          </div>
        )}
        {product.stock > 0 && product.stock <= 5 && (
          <div className="absolute top-2 right-2 bg-orange-500 text-white px-2 py-1 rounded text-xs font-semibold">
            Only {product.stock} left
          </div>
        )}
      </div>

      {/* Product Details */}
      <div className="p-6 flex-1 flex flex-col">
        {/* Category and Name */}
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 flex-1">
            {product.name}
          </h3>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded ml-2 whitespace-nowrap">
            {product.category}
          </span>
        </div>

        {/* Description */}
        <p className="text-gray-600 text-sm mb-3 line-clamp-2 flex-grow">
          {product.description}
        </p>

        {/* Rating */}
        {product.rating !== undefined && (
          <div className="flex items-center mb-3">
            <div className="flex items-center">
              {renderStars(product.rating)}
            </div>
            <span className="text-sm text-gray-600 ml-2">
              {product.rating.toFixed(1)}
              {product.reviews && ` (${product.reviews} reviews)`}
            </span>
          </div>
        )}

        {/* Price and Actions */}
        <div className="flex items-center justify-between mt-auto pt-4 border-t border-gray-100">
          <div>
            <span className="text-2xl font-bold text-blue-600">
              ${product.price.toFixed(2)}
            </span>
            {product.stock !== undefined && product.stock > 5 && (
              <p className="text-xs text-green-600 mt-1">In Stock</p>
            )}
          </div>

          <div className="flex gap-2">
            {!isOutOfStock && onAddToCart && (
              <button
                onClick={handleAddToCart}
                className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 transition-colors"
                title="Add to cart"
              >
                <ShoppingCart className="h-5 w-5" />
              </button>
            )}
            <span className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200 transition-colors">
              View Details
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}

export default ProductCard
