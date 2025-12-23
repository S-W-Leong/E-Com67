import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Grid, List, AlertCircle } from 'lucide-react'
import { productApi, cartApi } from '../services/api'
import ProductCard from '../components/ProductCard'
import SearchBar from '../components/SearchBar'
import { fetchAuthSession } from 'aws-amplify/auth'

/**
 * Products Page
 * Main product browsing interface with search, filtering, and pagination
 * Implements Requirements 2.2, 3.1, 3.3, 4.1 from design.md
 */
const Products = () => {
  const [searchParams, setSearchParams] = useSearchParams()

  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [lastKey, setLastKey] = useState(null)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  // Filters state
  const [filters, setFilters] = useState({
    category: searchParams.get('category') || '',
    priceRange: searchParams.get('priceRange') || '',
    sortBy: searchParams.get('sortBy') || 'name',
    searchQuery: searchParams.get('q') || ''
  })

  const categories = ['All', 'Electronics', 'Clothing', 'Home', 'Sports', 'Books', 'Toys']
  const priceRanges = [
    { label: 'All Prices', value: '' },
    { label: 'Under $50', value: '0-50' },
    { label: '$50 - $200', value: '50-200' },
    { label: '$200 - $500', value: '200-500' },
    { label: 'Over $500', value: '500+' }
  ]

  /**
   * Fetch products from API
   * Handles both initial load and pagination
   */
  const fetchProducts = useCallback(async (append = false) => {
    try {
      if (!append) {
        setLoading(true)
        setError(null)
      } else {
        setLoadingMore(true)
      }

      const params = {
        limit: 12
      }

      // Add category filter if set
      if (filters.category && filters.category !== 'All') {
        params.category = filters.category
      }

      // Add pagination key if loading more
      if (append && lastKey) {
        params.lastKey = lastKey
      }

      let response

      // Use search API if there's a search query
      if (filters.searchQuery) {
        response = await productApi.searchProducts(filters.searchQuery, params)
      } else {
        response = await productApi.getProducts(params)
      }

      const newProducts = response.products || []

      if (append) {
        setProducts(prev => [...prev, ...newProducts])
      } else {
        setProducts(newProducts)
      }

      setLastKey(response.lastKey)
      setHasMore(!!response.lastKey)

    } catch (err) {
      console.error('Error fetching products:', err)
      setError(err.response?.data?.error?.message || 'Failed to load products. Please try again.')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [filters.category, filters.searchQuery, lastKey])

  /**
   * Initial load and filter changes
   */
  useEffect(() => {
    setLastKey(null)
    setHasMore(true)
    fetchProducts(false)
  }, [filters.category, filters.searchQuery])

  /**
   * Update URL search params when filters change
   */
  useEffect(() => {
    const params = {}
    if (filters.category && filters.category !== 'All') params.category = filters.category
    if (filters.priceRange) params.priceRange = filters.priceRange
    if (filters.sortBy !== 'name') params.sortBy = filters.sortBy
    if (filters.searchQuery) params.q = filters.searchQuery

    setSearchParams(params)
  }, [filters, setSearchParams])

  /**
   * Client-side filtering and sorting
   * Applied to the fetched products for price range and sorting
   */
  const filteredProducts = products.filter(product => {
    // Price range filter
    if (filters.priceRange) {
      const [min, max] = filters.priceRange.split('-').map(Number)
      if (max) {
        if (product.price < min || product.price > max) return false
      } else if (filters.priceRange === '500+') {
        if (product.price < 500) return false
      }
    }
    return true
  }).sort((a, b) => {
    // Sorting
    switch (filters.sortBy) {
      case 'price-low':
        return a.price - b.price
      case 'price-high':
        return b.price - a.price
      case 'rating':
        return (b.rating || 0) - (a.rating || 0)
      default:
        return a.name.localeCompare(b.name)
    }
  })

  /**
   * Handle search submission
   */
  const handleSearch = (query) => {
    setFilters(prev => ({ ...prev, searchQuery: query }))
  }

  /**
   * Handle add to cart
   */
  const handleAddToCart = async (product) => {
    try {
      // Check if user is authenticated
      await fetchAuthSession()

      await cartApi.addToCart(product.productId, 1)

      // Show success feedback (you could use a toast notification here)
      alert(`${product.name} added to cart!`)
    } catch (error) {
      if (error.name === 'UserUnAuthenticatedException') {
        alert('Please sign in to add items to your cart')
      } else {
        console.error('Error adding to cart:', error)
        alert('Failed to add item to cart. Please try again.')
      }
    }
  }

  /**
   * Load more products (pagination)
   */
  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      fetchProducts(true)
    }
  }

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setFilters({
      category: '',
      priceRange: '',
      sortBy: 'name',
      searchQuery: ''
    })
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
            <h3 className="text-red-800 font-semibold mb-1">Error Loading Products</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => fetchProducts(false)}
              className="mt-3 text-red-600 hover:text-red-700 font-medium text-sm"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Products</h1>
        <p className="text-gray-600 mb-6">Discover our wide range of quality products</p>

        {/* Search Bar */}
        <SearchBar
          onSearch={handleSearch}
          initialValue={filters.searchQuery}
        />
      </div>

      {/* Active Search Query */}
      {filters.searchQuery && (
        <div className="mb-6 flex items-center gap-2">
          <span className="text-gray-600">Searching for:</span>
          <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-medium">
            {filters.searchQuery}
          </span>
          <button
            onClick={() => setFilters(prev => ({ ...prev, searchQuery: '' }))}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            Clear search
          </button>
        </div>
      )}

      {/* Filters and Controls */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4 flex-wrap">
            {/* Category Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={filters.category || 'All'}
                onChange={(e) => setFilters({...filters, category: e.target.value === 'All' ? '' : e.target.value})}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            {/* Price Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Price Range</label>
              <select
                value={filters.priceRange}
                onChange={(e) => setFilters({...filters, priceRange: e.target.value})}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {priceRanges.map(range => (
                  <option key={range.value} value={range.value}>
                    {range.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
              <select
                value={filters.sortBy}
                onChange={(e) => setFilters({...filters, sortBy: e.target.value})}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="name">Name</option>
                <option value="price-low">Price: Low to High</option>
                <option value="price-high">Price: High to Low</option>
                <option value="rating">Rating</option>
              </select>
            </div>

            {/* Clear Filters */}
            {(filters.category || filters.priceRange || filters.sortBy !== 'name') && (
              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  Clear filters
                </button>
              </div>
            )}
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">View:</span>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
              title="Grid view"
            >
              <Grid className="h-5 w-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-md ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
              title="List view"
            >
              <List className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="mb-6">
        <p className="text-gray-600">
          Showing {filteredProducts.length} {filteredProducts.length === 1 ? 'product' : 'products'}
        </p>
      </div>

      {/* Products Grid/List */}
      {filteredProducts.length > 0 ? (
        <>
          <div className={viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
            : 'space-y-6'
          }>
            {filteredProducts.map((product) => (
              <ProductCard
                key={product.productId}
                product={product}
                viewMode={viewMode}
                onAddToCart={handleAddToCart}
              />
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="mt-8 text-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loadingMore ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Loading...
                  </span>
                ) : (
                  'Load More Products'
                )}
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No products found matching your criteria.</p>
          <button
            onClick={clearFilters}
            className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
          >
            Clear all filters
          </button>
        </div>
      )}
    </div>
  )
}

export default Products
