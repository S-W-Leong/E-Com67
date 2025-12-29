import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Star, ShoppingCart, ArrowLeft, AlertCircle, Plus, Minus, Check } from 'lucide-react'
import { productApi, cartApi } from '../services/api'
import { fetchAuthSession } from 'aws-amplify/auth'
import { metaPixel } from '../services/metaPixel'

/**
 * ProductDetail Page
 * Displays detailed product information with add-to-cart functionality
 * Implements Requirements 2.2, 4.1 from design.md
 */
const ProductDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()

  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [quantity, setQuantity] = useState(1)
  const [addingToCart, setAddingToCart] = useState(false)
  const [addedToCart, setAddedToCart] = useState(false)
  const [relatedProducts, setRelatedProducts] = useState([])

  /**
   * Fetch product details on component mount
   */
  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true)
        setError(null)

        const data = await productApi.getProduct(id)
        setProduct(data)

        // Track Meta Pixel ViewContent event
        metaPixel.trackViewContent(data)

        // Fetch related products (same category)
        if (data.category) {
          try {
            const related = await productApi.getProducts({
              category: data.category,
              limit: 4
            })
            // Filter out current product
            setRelatedProducts(
              (related.products || []).filter(p => p.productId !== id).slice(0, 3)
            )
          } catch (err) {
            console.error('Error fetching related products:', err)
          }
        }
      } catch (err) {
        console.error('Error fetching product:', err)
        setError(err.response?.data?.error?.message || 'Failed to load product details.')
      } finally {
        setLoading(false)
      }
    }

    fetchProduct()
  }, [id])

  /**
   * Handle add to cart
   */
  const handleAddToCart = async () => {
    try {
      setAddingToCart(true)

      // Check if user is authenticated
      await fetchAuthSession()

      await cartApi.addToCart(product.productId, quantity)

      // Track Meta Pixel AddToCart event
      metaPixel.trackAddToCart(product, quantity)

      setAddedToCart(true)
      setTimeout(() => setAddedToCart(false), 3000)
    } catch (error) {
      if (error.name === 'UserUnAuthenticatedException') {
        // Redirect to login (Amplify will handle this)
        alert('Please sign in to add items to your cart')
      } else {
        console.error('Error adding to cart:', error)
        alert('Failed to add item to cart. Please try again.')
      }
    } finally {
      setAddingToCart(false)
    }
  }

  /**
   * Handle buy now (add to cart and navigate to cart)
   */
  const handleBuyNow = async () => {
    try {
      setAddingToCart(true)

      await fetchAuthSession()
      await cartApi.addToCart(product.productId, quantity)

      // Track Meta Pixel AddToCart event (for Buy Now)
      metaPixel.trackAddToCart(product, quantity)

      navigate('/cart')
    } catch (error) {
      if (error.name === 'UserUnAuthenticatedException') {
        alert('Please sign in to continue')
      } else {
        console.error('Error adding to cart:', error)
        alert('Failed to add item to cart. Please try again.')
      }
      setAddingToCart(false)
    }
  }

  /**
   * Render star rating
   */
  const renderStars = (rating) => {
    return [...Array(5)].map((_, i) => (
      <Star
        key={i}
        className={`h-5 w-5 ${
          i < Math.floor(rating)
            ? 'text-yellow-400 fill-current'
            : 'text-gray-300'
        }`}
      />
    ))
  }

  /**
   * Increase quantity
   */
  const increaseQuantity = () => {
    if (product && quantity < product.stock) {
      setQuantity(prev => prev + 1)
    }
  }

  /**
   * Decrease quantity
   */
  const decreaseQuantity = () => {
    if (quantity > 1) {
      setQuantity(prev => prev - 1)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-start gap-3">
          <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-red-800 font-semibold mb-1">Error Loading Product</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => navigate('/products')}
              className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Back to Products
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <p className="text-center text-gray-500">Product not found</p>
      </div>
    )
  }

  const isOutOfStock = product.stock === 0
  const isLowStock = product.stock > 0 && product.stock <= 5

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="h-5 w-5" />
        Back
      </button>

      {/* Product Detail Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* Product Image */}
        <div className="relative">
          <img
            src={product.imageUrl || 'https://via.placeholder.com/600x600?text=No+Image'}
            alt={product.name}
            className="w-full h-auto rounded-lg shadow-md"
          />
          {isOutOfStock && (
            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-lg">
              <span className="bg-red-600 text-white px-6 py-3 rounded-md font-semibold text-lg">
                Out of Stock
              </span>
            </div>
          )}
        </div>

        {/* Product Info */}
        <div>
          {/* Category */}
          <div className="mb-2">
            <Link
              to={`/products?category=${product.category}`}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {product.category}
            </Link>
          </div>

          {/* Title */}
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {product.name}
          </h1>

          {/* Rating */}
          {product.rating !== undefined && (
            <div className="flex items-center mb-4">
              <div className="flex items-center">
                {renderStars(product.rating)}
              </div>
              <span className="text-gray-600 ml-2">
                {product.rating.toFixed(1)}
                {product.reviews && ` (${product.reviews} reviews)`}
              </span>
            </div>
          )}

          {/* Price */}
          <div className="mb-6">
            <span className="text-4xl font-bold text-blue-600">
              ${product.price.toFixed(2)}
            </span>
          </div>

          {/* Stock Status */}
          <div className="mb-6">
            {isOutOfStock ? (
              <p className="text-red-600 font-semibold">Out of Stock</p>
            ) : isLowStock ? (
              <p className="text-orange-600 font-semibold">
                Only {product.stock} left in stock
              </p>
            ) : (
              <p className="text-green-600 font-semibold">In Stock</p>
            )}
          </div>

          {/* Description */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Description</h2>
            <p className="text-gray-700 leading-relaxed">
              {product.description}
            </p>
          </div>

          {/* Tags */}
          {product.tags && product.tags.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Tags</h2>
              <div className="flex flex-wrap gap-2">
                {product.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quantity Selector and Add to Cart */}
          {!isOutOfStock && (
            <div className="space-y-4">
              {/* Quantity Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <div className="flex items-center gap-3">
                  <button
                    onClick={decreaseQuantity}
                    disabled={quantity <= 1}
                    className="p-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <span className="text-lg font-semibold w-12 text-center">
                    {quantity}
                  </span>
                  <button
                    onClick={increaseQuantity}
                    disabled={quantity >= product.stock}
                    className="p-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-500 ml-2">
                    {product.stock} available
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleAddToCart}
                  disabled={addingToCart || isOutOfStock}
                  className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {addingToCart ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Adding...
                    </>
                  ) : addedToCart ? (
                    <>
                      <Check className="h-5 w-5" />
                      Added to Cart
                    </>
                  ) : (
                    <>
                      <ShoppingCart className="h-5 w-5" />
                      Add to Cart
                    </>
                  )}
                </button>

                <button
                  onClick={handleBuyNow}
                  disabled={addingToCart || isOutOfStock}
                  className="flex-1 bg-gray-900 text-white px-6 py-3 rounded-md hover:bg-gray-800 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  Buy Now
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Related Products */}
      {relatedProducts.length > 0 && (
        <div className="mt-12 pt-12 border-t border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Related Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {relatedProducts.map((related) => (
              <Link
                key={related.productId}
                to={`/products/${related.productId}`}
                className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <img
                  src={related.imageUrl || 'https://via.placeholder.com/300x300'}
                  alt={related.name}
                  className="w-full h-48 object-cover"
                />
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                    {related.name}
                  </h3>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-blue-600">
                      ${related.price.toFixed(2)}
                    </span>
                    {related.rating && (
                      <div className="flex items-center text-sm text-gray-600">
                        <Star className="h-4 w-4 text-yellow-400 fill-current mr-1" />
                        {related.rating.toFixed(1)}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ProductDetail
