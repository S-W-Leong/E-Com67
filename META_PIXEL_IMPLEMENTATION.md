# Meta Pixel Implementation Checklist

## Overview
This checklist guides the implementation of Meta Pixel tracking for the E-Com67 customer-facing application to enable ad optimization, audience building, and conversion tracking.

**Target Application**: Customer App only (not Admin Dashboard)

---

## Phase 1: Setup & Configuration

### 1.1 Meta Business Setup
- [x] Create Meta Business Manager account (if not exists)
- [x] Navigate to Events Manager in Meta Business Suite
- [x] Create a new Meta Pixel for E-Com67
- [x] Copy the Pixel ID (format: 15-16 digit number)
- [x] Note Pixel ID: `845200948278825`

### 1.2 Install Dependencies
- [ ] Navigate to customer app directory:
  ```bash
  cd frontends/customer-app
  ```
- [ ] Install Meta Pixel package:
  ```bash
  npm install react-facebook-pixel
  ```
- [ ] Verify installation in `package.json`

### 1.3 Environment Configuration
- [ ] Create/update `.env.local` in `frontends/customer-app/`:
  ```bash
  VITE_META_PIXEL_ID=your_pixel_id_here
  ```
- [ ] Add `.env.local` to `.gitignore` (verify it's already there)
- [ ] For production: Store Pixel ID in AWS Systems Manager Parameter Store:
  ```bash
  aws ssm put-parameter \
    --name "/e-com67/meta-pixel-id" \
    --value "YOUR_PRODUCTION_PIXEL_ID" \
    --type "String" \
    --region ap-southeast-1
  ```

---

## Phase 2: Core Implementation

### 2.1 Create Meta Pixel Service
- [ ] Create file: `frontends/customer-app/src/services/metaPixel.js`
- [ ] Copy the MetaPixelService class implementation
- [ ] Implement the following methods:
  - [ ] `init()` - Initialize Pixel
  - [ ] `trackPageView()` - Track page views
  - [ ] `trackViewContent(product)` - Track product views
  - [ ] `trackSearch(searchQuery)` - Track searches
  - [ ] `trackAddToCart(product, quantity)` - Track add to cart
  - [ ] `trackInitiateCheckout(cart)` - Track checkout start
  - [ ] `trackPurchase(order)` - Track completed purchases
- [ ] Export singleton instance

### 2.2 Initialize in App Component
- [ ] Open `frontends/customer-app/src/App.jsx`
- [ ] Import Meta Pixel service:
  ```javascript
  import { metaPixel } from './services/metaPixel';
  ```
- [ ] Add initialization in `useEffect` on mount:
  ```javascript
  useEffect(() => {
    metaPixel.init();
  }, []);
  ```
- [ ] Add page view tracking on route changes:
  ```javascript
  import { useLocation } from 'react-router-dom';
  const location = useLocation();

  useEffect(() => {
    metaPixel.trackPageView();
  }, [location.pathname]);
  ```

---

## Phase 3: Event Tracking Implementation

### 3.1 Product Detail Page
- [ ] Locate product detail component (likely `ProductDetail.jsx` or similar)
- [ ] Import Meta Pixel service
- [ ] Add `trackViewContent` when product loads:
  ```javascript
  useEffect(() => {
    if (product) {
      metaPixel.trackViewContent(product);
    }
  }, [product]);
  ```
- [ ] Test: Navigate to product page and verify event fires

### 3.2 Search Functionality
- [ ] Locate search component (likely `SearchBar.jsx` or similar)
- [ ] Import Meta Pixel service
- [ ] Add `trackSearch` when search is executed:
  ```javascript
  const handleSearch = (query) => {
    // Existing search logic...
    metaPixel.trackSearch(query);
  };
  ```
- [ ] Test: Perform search and verify event fires

### 3.3 Add to Cart
- [ ] Locate cart component or product card component
- [ ] Import Meta Pixel service
- [ ] Add `trackAddToCart` in add to cart handler:
  ```javascript
  const handleAddToCart = (product, quantity) => {
    // Existing add to cart logic...
    addToCart(product, quantity);
    metaPixel.trackAddToCart(product, quantity);
  };
  ```
- [ ] Test: Add item to cart and verify event fires

### 3.4 Checkout Initiation
- [ ] Locate checkout component (likely `Checkout.jsx`)
- [ ] Import Meta Pixel service
- [ ] Add `trackInitiateCheckout` when checkout page loads:
  ```javascript
  useEffect(() => {
    if (cart && cart.items.length > 0) {
      metaPixel.trackInitiateCheckout(cart);
    }
  }, [cart]);
  ```
- [ ] Test: Navigate to checkout and verify event fires

### 3.5 Purchase Completion
- [ ] Locate order confirmation component (likely `CheckoutSuccess.jsx` or `OrderConfirmation.jsx`)
- [ ] Import Meta Pixel service
- [ ] Add `trackPurchase` when order is confirmed:
  ```javascript
  useEffect(() => {
    if (order) {
      metaPixel.trackPurchase(order);
    }
  }, [order]);
  ```
- [ ] Test: Complete a test purchase and verify event fires

---

## Phase 4: Testing & Validation

### 4.1 Development Testing Setup
- [ ] Install Meta Pixel Helper Chrome extension
  - URL: https://chrome.google.com/webstore (search "Meta Pixel Helper")
- [ ] Start local development server:
  ```bash
  cd frontends/customer-app
  npm run dev
  ```
- [ ] Open browser with Meta Pixel Helper extension enabled
- [ ] Open browser console to see debug logs

### 4.2 Test Each Event
- [ ] **PageView**: Navigate between pages → Check console & Pixel Helper
- [ ] **ViewContent**: Open product detail page → Verify product data sent
- [ ] **Search**: Perform search → Verify search term sent
- [ ] **AddToCart**: Add item to cart → Verify product ID and value sent
- [ ] **InitiateCheckout**: Go to checkout → Verify cart total sent
- [ ] **Purchase**: Complete test order → Verify order ID and value sent

### 4.3 Meta Events Manager Validation
- [ ] Log into Meta Business Suite → Events Manager
- [ ] Select your Pixel
- [ ] Go to "Test Events" tab
- [ ] Enter your test device browser info
- [ ] Perform test actions on your site
- [ ] Verify events appear in real-time in Events Manager
- [ ] Check that event parameters are correct

### 4.4 Event Quality Check
- [ ] Verify all events have correct parameters:
  - [ ] `content_ids` contains product IDs
  - [ ] `value` contains correct prices
  - [ ] `currency` is set to USD (or your currency)
  - [ ] `content_type` is set appropriately
- [ ] Verify no duplicate events are firing
- [ ] Check for any console errors or warnings

---

## Phase 5: Deployment

### 5.1 Production Configuration
- [ ] Obtain production Meta Pixel ID from Meta Business Suite
- [ ] Store in AWS Systems Manager Parameter Store (see step 1.3)
- [ ] Update frontend build process to inject Pixel ID from Parameter Store
- [ ] Document Pixel ID location for team

### 5.2 Build & Deploy
- [ ] Build customer app:
  ```bash
  cd frontends/customer-app
  npm run build
  ```
- [ ] Test production build locally:
  ```bash
  npm run preview
  ```
- [ ] Deploy to S3 using existing pipeline or manual deploy:
  ```bash
  aws s3 sync dist/ s3://e-com67-customer-app-YOUR_ACCOUNT --delete
  ```
- [ ] Invalidate CloudFront cache:
  ```bash
  aws cloudfront create-invalidation \
    --distribution-id YOUR_DIST_ID \
    --paths "/*"
  ```

### 5.3 Production Verification
- [ ] Visit production customer app URL
- [ ] Use Meta Pixel Helper to verify Pixel is active
- [ ] Test critical events (PageView, AddToCart, Purchase)
- [ ] Monitor Events Manager for incoming production events
- [ ] Verify event data quality in production

---

## Phase 6: Monitoring & Optimization

### 6.1 Initial Monitoring (First 7 Days)
- [ ] Monitor Events Manager daily
- [ ] Check for event quality score (aim for "Good")
- [ ] Review event match quality (email, phone, etc.)
- [ ] Verify Purchase events match actual orders in DynamoDB
- [ ] Check for any error events or missing parameters

### 6.2 Pixel Health Dashboard
- [ ] Set up regular checks in Meta Events Manager:
  - [ ] Event count trends
  - [ ] Parameter completeness
  - [ ] Match quality score
  - [ ] Error rate
- [ ] Document baseline metrics for comparison

### 6.3 Troubleshooting Common Issues
- [ ] **Events not firing**: Check browser console for errors
- [ ] **Duplicate events**: Review component mounting and useEffect dependencies
- [ ] **Missing parameters**: Verify data structure matches expected format
- [ ] **Low match quality**: Consider implementing advanced matching
- [ ] **Ad blocker interference**: Document known limitations

---

## Phase 7: Documentation & Handoff

### 7.1 Technical Documentation
- [ ] Update `frontends/customer-app/README.md` with Meta Pixel info
- [ ] Document environment variables in project README
- [ ] Add Meta Pixel service to architecture documentation
- [ ] Create troubleshooting guide for common issues

### 7.2 Privacy & Compliance Documentation
- [ ] Document what data is collected by Meta Pixel
- [ ] Update privacy policy (if customer-facing)
- [ ] Note: Cookie consent not implemented (future enhancement)
- [ ] Add disclaimer about Meta tracking in user agreements

### 7.3 Team Handoff
- [ ] Share Meta Business Manager access with relevant team members
- [ ] Provide Events Manager training or documentation
- [ ] Document where Pixel ID is stored (Parameter Store)
- [ ] Create runbook for common maintenance tasks

---

## Optional Enhancements (Future)

### Cookie Consent Management
- [ ] Research GDPR/CCPA requirements for your regions
- [ ] Implement cookie consent banner
- [ ] Conditionally initialize Pixel based on consent
- [ ] Add opt-out mechanism

### Meta Conversions API (Server-Side Tracking)
- [ ] Create Lambda function for server-side events
- [ ] Implement event deduplication with `eventID`
- [ ] Send Purchase events from order processor Lambda
- [ ] Enable advanced matching with hashed user data

### Advanced Matching
- [ ] Collect user email from Cognito (with consent)
- [ ] Hash email client-side before sending to Meta
- [ ] Pass hashed email in Pixel init options
- [ ] Improve match quality score

---

## Success Criteria

**Implementation is complete when:**
- ✅ All 6 standard events are firing correctly
- ✅ Events appear in Meta Events Manager with correct parameters
- ✅ Event quality score is "Good" or better
- ✅ Production deployment is successful
- ✅ No console errors related to Meta Pixel
- ✅ Team has access to Events Manager
- ✅ Documentation is updated

---

## Support Resources

- **Meta Pixel Documentation**: https://developers.facebook.com/docs/meta-pixel
- **Events Manager**: https://business.facebook.com/events_manager
- **Meta Pixel Helper**: Chrome Web Store
- **react-facebook-pixel Docs**: https://www.npmjs.com/package/react-facebook-pixel
- **Event Reference**: https://developers.facebook.com/docs/meta-pixel/reference

---

**Started**: _______________
**Completed**: _______________
**Implemented by**: _______________
