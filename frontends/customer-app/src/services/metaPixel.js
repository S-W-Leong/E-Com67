import ReactPixel from 'react-facebook-pixel';

/**
 * Meta Pixel Service
 * Handles all Meta Pixel tracking events for the E-Com67 customer app
 */
class MetaPixelService {
  constructor() {
    this.initialized = false;
    this.pixelId = import.meta.env.VITE_META_PIXEL_ID;
  }

  /**
   * Initialize Meta Pixel
   * Should be called once on app mount
   */
  init() {
    if (!this.pixelId) {
      console.warn('Meta Pixel ID not configured - skipping initialization');
      return;
    }

    if (this.initialized) {
      console.warn('Meta Pixel already initialized');
      return;
    }

    const options = {
      autoConfig: true, // Enable automatic advanced matching
      debug: import.meta.env.DEV, // Enable debug mode in development
    };

    ReactPixel.init(this.pixelId, options);
    this.initialized = true;
    console.log('Meta Pixel initialized:', this.pixelId);
  }

  /**
   * Track page view
   * Call this on route changes
   */
  trackPageView() {
    if (!this.initialized) return;
    ReactPixel.pageView();
    console.log('Meta Pixel: PageView tracked');
  }

  /**
   * Track product view
   * @param {Object} product - Product object with productId, name, price, category
   */
  trackViewContent(product) {
    if (!this.initialized) return;
    ReactPixel.track('ViewContent', {
      content_ids: [product.productId],
      content_name: product.name,
      content_type: 'product',
      content_category: product.category,
      value: product.price,
      currency: 'USD',
    });
    console.log('Meta Pixel: ViewContent tracked', product.name);
  }

  /**
   * Track search
   * @param {string} searchQuery - Search term
   */
  trackSearch(searchQuery) {
    if (!this.initialized) return;
    ReactPixel.track('Search', {
      search_string: searchQuery,
    });
    console.log('Meta Pixel: Search tracked', searchQuery);
  }

  /**
   * Track add to cart
   * @param {Object} product - Product object
   * @param {number} quantity - Quantity added
   */
  trackAddToCart(product, quantity) {
    if (!this.initialized) return;
    ReactPixel.track('AddToCart', {
      content_ids: [product.productId],
      content_name: product.name,
      content_type: 'product',
      value: product.price * quantity,
      currency: 'USD',
    });
    console.log('Meta Pixel: AddToCart tracked', product.name, 'x', quantity);
  }

  /**
   * Track checkout initiation
   * @param {Object} cart - Cart object with items array
   */
  trackInitiateCheckout(cart) {
    if (!this.initialized) return;
    const totalValue = cart.items.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
    ReactPixel.track('InitiateCheckout', {
      content_ids: cart.items.map(item => item.productId),
      num_items: cart.items.length,
      value: totalValue,
      currency: 'USD',
    });
    console.log('Meta Pixel: InitiateCheckout tracked', totalValue);
  }

  /**
   * Track purchase completion
   * @param {Object} order - Order object with items, totalAmount, orderId
   */
  trackPurchase(order) {
    if (!this.initialized) return;
    ReactPixel.track('Purchase', {
      content_ids: order.items.map(item => item.productId),
      content_type: 'product',
      value: order.totalAmount,
      currency: 'USD',
      num_items: order.items.length,
    });
    console.log('Meta Pixel: Purchase tracked', order.orderId, order.totalAmount);
  }
}

// Export singleton instance
export const metaPixel = new MetaPixelService();
