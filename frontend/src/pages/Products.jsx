import { useState, useEffect } from 'react';
import { productsAPI } from '../services/api';
import ProductCard from '../components/ProductCard';
import SearchBar from '../components/SearchBar';
import LoadingSpinner from '../components/LoadingSpinner';
import toast from 'react-hot-toast';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await productsAPI.getAll();
      setProducts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load products:', error);
      toast.error('Failed to load products');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);

    if (!query.trim()) {
      loadProducts();
      return;
    }

    setLoading(true);
    try {
      const results = await productsAPI.search(query);
      setProducts(Array.isArray(results) ? results : []);
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2 gradient-text">Discover Products</h1>
        <p className="text-gray-600">Find the perfect items for you</p>
      </div>

      <SearchBar onSearch={handleSearch} />

      {/* Products Grid */}
      {loading ? (
        <LoadingSpinner message="Loading products..." />
      ) : products.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">No products found</h3>
          <p className="text-gray-600 mb-6">
            {searchQuery
              ? `No results for "${searchQuery}". Try a different search.`
              : 'No products available in this category.'}
          </p>
          {searchQuery && (
            <button onClick={() => handleSearch('')} className="btn-primary">
              Clear Search
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="mb-4 text-gray-600">
            Showing {products.length} product{products.length !== 1 ? 's' : ''}
            {searchQuery && ` for "${searchQuery}"`}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {products.map((product) => (
              <ProductCard key={product.productId} product={product} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default Products;
