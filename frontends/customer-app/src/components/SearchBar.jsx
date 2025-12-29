import React, { useState, useEffect, useRef } from 'react'
import { Search, X, TrendingUp } from 'lucide-react'
import { productApi } from '../services/api'
import { metaPixel } from '../services/metaPixel'

/**
 * SearchBar Component
 * Provides product search with autocomplete suggestions
 *
 * @param {Function} onSearch - Callback when search is submitted
 * @param {string} placeholder - Placeholder text
 * @param {string} initialValue - Initial search value
 */
const SearchBar = ({ onSearch, placeholder = 'Search products...', initialValue = '' }) => {
  const [query, setQuery] = useState(initialValue)
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [recentSearches, setRecentSearches] = useState([])
  const searchRef = useRef(null)
  const debounceTimer = useRef(null)

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('recentSearches')
    if (saved) {
      setRecentSearches(JSON.parse(saved))
    }
  }, [])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch suggestions when query changes
  useEffect(() => {
    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // Don't fetch if query is too short
    if (query.trim().length < 2) {
      setSuggestions([])
      return
    }

    // Debounce the search
    debounceTimer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const results = await productApi.searchProducts(query, { limit: 5 })
        setSuggestions(results.products || [])
      } catch (error) {
        console.error('Error fetching suggestions:', error)
        setSuggestions([])
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [query])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) {
      performSearch(query.trim())
    }
  }

  const performSearch = (searchQuery) => {
    // Save to recent searches
    const updated = [searchQuery, ...recentSearches.filter(s => s !== searchQuery)].slice(0, 5)
    setRecentSearches(updated)
    localStorage.setItem('recentSearches', JSON.stringify(updated))

    // Track Meta Pixel Search event
    metaPixel.trackSearch(searchQuery)

    // Close suggestions and perform search
    setShowSuggestions(false)
    if (onSearch) {
      onSearch(searchQuery)
    }
  }

  const handleSuggestionClick = (product) => {
    setQuery(product.name)
    setShowSuggestions(false)
    if (onSearch) {
      onSearch(product.name)
    }
  }

  const handleRecentSearchClick = (search) => {
    setQuery(search)
    performSearch(search)
  }

  const clearSearch = () => {
    setQuery('')
    setSuggestions([])
    setShowSuggestions(false)
  }

  const clearRecentSearches = () => {
    setRecentSearches([])
    localStorage.removeItem('recentSearches')
  }

  const shouldShowRecent = showSuggestions && query.trim().length === 0 && recentSearches.length > 0

  return (
    <div ref={searchRef} className="relative w-full max-w-2xl">
      {/* Search Form */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-3 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            placeholder={placeholder}
            className="w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {query && (
            <button
              type="button"
              onClick={clearSearch}
              className="absolute right-3 text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </form>

      {/* Suggestions Dropdown */}
      {showSuggestions && (
        <div className="absolute z-50 w-full mt-2 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-y-auto">
          {/* Loading State */}
          {loading && (
            <div className="p-4 text-center text-gray-500">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            </div>
          )}

          {/* Recent Searches */}
          {shouldShowRecent && (
            <div className="p-2">
              <div className="flex items-center justify-between px-3 py-2">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <TrendingUp className="h-4 w-4" />
                  Recent Searches
                </div>
                <button
                  onClick={clearRecentSearches}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Clear
                </button>
              </div>
              {recentSearches.map((search, index) => (
                <button
                  key={index}
                  onClick={() => handleRecentSearchClick(search)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 rounded-md text-sm text-gray-700"
                >
                  {search}
                </button>
              ))}
            </div>
          )}

          {/* Product Suggestions */}
          {!loading && suggestions.length > 0 && query.trim().length >= 2 && (
            <div className="p-2">
              <div className="px-3 py-2 text-sm font-medium text-gray-700">
                Products
              </div>
              {suggestions.map((product) => (
                <button
                  key={product.productId}
                  onClick={() => handleSuggestionClick(product)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 rounded-md flex items-center gap-3"
                >
                  <img
                    src={product.imageUrl || 'https://via.placeholder.com/40x40'}
                    alt={product.name}
                    className="w-10 h-10 object-cover rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {product.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      ${product.price.toFixed(2)} · {product.category}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* No Results */}
          {!loading && suggestions.length === 0 && query.trim().length >= 2 && (
            <div className="p-4 text-center text-gray-500 text-sm">
              No products found for "{query}"
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SearchBar
