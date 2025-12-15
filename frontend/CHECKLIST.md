# E-Com67 Frontend - Testing Checklist

## 🚀 Before You Start

- [ ] Backend CDK stack is deployed
- [ ] Environment variables are set in root `.env.local`
- [ ] Dependencies installed (`npm install` completed)
- [ ] Development server can start (`npm run dev`)

## ✅ Feature Testing Checklist

### 1. Authentication (Login/Signup)

#### Sign Up Flow
- [ ] Navigate to the app (should redirect to login)
- [ ] Click "Sign Up" button
- [ ] Enter valid email address
- [ ] Enter password (min 8 characters)
- [ ] Submit form
- [ ] Check email for verification code
- [ ] Enter verification code
- [ ] Confirmation successful message appears
- [ ] Redirected to login

#### Sign In Flow
- [ ] Enter registered email
- [ ] Enter correct password
- [ ] Click "Sign In"
- [ ] Successfully redirected to Products page
- [ ] Navbar appears with user email
- [ ] Logout button visible

#### Error Handling
- [ ] Try sign up with existing email (should show error)
- [ ] Try login with wrong password (should show error)
- [ ] Try login with non-existent email (should show error)

### 2. Products Page

#### Display
- [ ] Products load and display
- [ ] Product cards show image placeholder if no image
- [ ] Product name, description, price visible
- [ ] Category displayed on each card
- [ ] "Add to Cart" button visible
- [ ] Out of stock products show "Out of Stock" badge

#### Category Filtering
- [ ] Click "All Products" - shows all products
- [ ] Click "Electronics" - filters to Electronics only
- [ ] Click "Clothing" - filters to Clothing only
- [ ] Click "Books" - filters to Books only
- [ ] Click "Home" - filters to Home only
- [ ] Click "Sports" - filters to Sports only
- [ ] Click "Beauty" - filters to Beauty only
- [ ] Product count updates correctly

#### Search Functionality
- [ ] Enter search term in search bar
- [ ] Press Enter or click search icon
- [ ] Results match search query
- [ ] "No products found" shows if no matches
- [ ] Clear search returns to all products
- [ ] Search result count displayed

#### Add to Cart
- [ ] Click "Add to Cart" on a product
- [ ] Loading spinner shows briefly
- [ ] Success toast notification appears
- [ ] Button returns to normal state
- [ ] Product added to cart (verify in Cart page)

### 3. Shopping Cart

#### Display
- [ ] Navigate to Cart page
- [ ] Cart items display correctly
- [ ] Product images show (or placeholder)
- [ ] Product name, description, price visible
- [ ] Quantity controls visible
- [ ] Remove button present
- [ ] Subtotal calculation correct
- [ ] Tax calculation (10%) correct
- [ ] Total calculation correct

#### Quantity Management
- [ ] Click "-" button decreases quantity
- [ ] Click "+" button increases quantity
- [ ] Minimum quantity is 1 (can't go below)
- [ ] Item subtotal updates
- [ ] Cart total updates
- [ ] Toast notification on update

#### Remove Items
- [ ] Click "Remove" button
- [ ] Confirmation or immediate removal
- [ ] Item removed from cart
- [ ] Total recalculates
- [ ] Toast notification shows

#### Empty Cart
- [ ] Remove all items
- [ ] "Cart is empty" message appears
- [ ] "Continue Shopping" button visible
- [ ] Click button returns to Products

#### Navigation
- [ ] "Proceed to Checkout" button visible when cart has items
- [ ] Click button navigates to Checkout page
- [ ] "Continue Shopping" returns to Products

### 4. Checkout

#### Display
- [ ] Navigate to Checkout from Cart
- [ ] Order summary shows all cart items
- [ ] Item quantities and prices correct
- [ ] Subtotal, tax, shipping, total correct
- [ ] Shipping shows as FREE
- [ ] Payment form visible
- [ ] Demo mode notice visible

#### Payment Form
- [ ] Enter cardholder name (any text)
- [ ] Enter card number (test: 4242 4242 4242 4242)
- [ ] Enter expiry date (any future date)
- [ ] Enter CVV (any 3-4 digits)
- [ ] All fields required (can't submit empty)

#### Submit Order
- [ ] Fill all payment fields
- [ ] Click "Pay $XX.XX" button
- [ ] "Processing payment..." toast appears
- [ ] Button shows loading state
- [ ] "Payment successful!" toast appears
- [ ] "Order placed successfully!" toast appears
- [ ] Redirected to Orders page after ~1.5s

#### Error Handling
- [ ] Try submitting with empty fields (should prevent)
- [ ] Network error handling (if backend down)

### 5. Orders History

#### Display
- [ ] Navigate to Orders page
- [ ] Recent order appears at top
- [ ] Order ID shown (first 8 characters)
- [ ] Order date and time formatted correctly
- [ ] Status badge shows (Processing, Completed, etc.)
- [ ] Total amount displayed correctly
- [ ] "View Details" button visible

#### Order Details Modal
- [ ] Click "View Details" on an order
- [ ] Modal opens
- [ ] Order ID (full) displayed
- [ ] Order date/time shown
- [ ] Status badge visible
- [ ] Payment ID shown
- [ ] All order items listed
- [ ] Item quantities and prices correct
- [ ] Total amount correct
- [ ] Close button works (X icon)
- [ ] Click outside modal closes it

#### Empty State
- [ ] Delete/clear all orders (if possible)
- [ ] "No orders yet" message shows
- [ ] "Browse Products" button visible
- [ ] Click button returns to Products

### 6. AI Chat Widget

#### Display
- [ ] Floating chat button visible (bottom right)
- [ ] Click button opens chat window
- [ ] Chat window shows header "AI Shopping Assistant"
- [ ] Connection status indicator visible
- [ ] Welcome message appears
- [ ] Message input field visible
- [ ] Send button visible

#### Messaging
- [ ] Type a message in input field
- [ ] Press Enter or click Send
- [ ] User message appears (right side, blue)
- [ ] Loading/typing indicator (optional)
- [ ] AI response appears (left side, white)
- [ ] Timestamp shows on messages
- [ ] Messages auto-scroll to bottom

#### Demo Responses
- [ ] Send "hello" - gets greeting response
- [ ] Send "help" - gets help message
- [ ] Send "product" - gets product recommendation
- [ ] Send "price" - gets pricing help
- [ ] Send random text - gets demo mode message

#### Window Controls
- [ ] Click X button closes chat
- [ ] Chat button reappears
- [ ] Reopen chat - messages persist in session
- [ ] Minimize/maximize works smoothly

### 7. Navigation & Routing

#### Navbar Links
- [ ] Click "E-Com67" logo - goes to Products
- [ ] Click "Products" - goes to Products
- [ ] Click "Cart" - goes to Cart
- [ ] Click "Orders" - goes to Orders
- [ ] All links highlight active page

#### Logout
- [ ] Click "Logout" button
- [ ] "Logged out successfully" toast appears
- [ ] Redirected to Login page
- [ ] Cannot access protected pages
- [ ] Navbar disappears
- [ ] Chat widget disappears

#### Protected Routes
- [ ] Try accessing `/products` when logged out - redirects to login
- [ ] Try accessing `/cart` when logged out - redirects to login
- [ ] Try accessing `/checkout` when logged out - redirects to login
- [ ] Try accessing `/orders` when logged out - redirects to login

#### 404 Page
- [ ] Navigate to `/invalid-route`
- [ ] 404 page appears
- [ ] "Page Not Found" message shows
- [ ] "Go Back" button works
- [ ] "Go to Products" button works

### 8. Responsive Design

#### Mobile (< 640px)
- [ ] Login page looks good
- [ ] Products grid switches to 1 column
- [ ] Navbar is responsive
- [ ] Cart page is readable
- [ ] Checkout form is usable
- [ ] Chat widget doesn't overlap content

#### Tablet (640px - 1024px)
- [ ] Products grid shows 2-3 columns
- [ ] Cart layout stacks properly
- [ ] Checkout splits properly
- [ ] All text is readable

#### Desktop (> 1024px)
- [ ] Products grid shows 4 columns
- [ ] Cart shows 2-column layout
- [ ] Checkout shows 2-column layout
- [ ] All spacing looks good

### 9. Error Handling

#### Network Errors
- [ ] Stop backend server
- [ ] Try loading products - shows error toast
- [ ] Try adding to cart - shows error toast
- [ ] Try checkout - shows error toast
- [ ] Error messages are user-friendly

#### React Errors
- [ ] Error boundary catches component errors
- [ ] Error page shows with details (dev mode)
- [ ] "Reload Page" button works
- [ ] "Go Home" button works

#### Loading States
- [ ] Products page shows spinner while loading
- [ ] Cart shows spinner while loading
- [ ] Orders shows spinner while loading
- [ ] Checkout shows spinner while processing
- [ ] All buttons show loading state when clicked

### 10. Toast Notifications

- [ ] Success toasts are green
- [ ] Error toasts are red
- [ ] Toasts appear top-right
- [ ] Toasts auto-dismiss after 3-4 seconds
- [ ] Multiple toasts stack properly
- [ ] Toast messages are clear and helpful

### 11. Performance

- [ ] Initial page load is fast (< 2s)
- [ ] Navigation between pages is instant
- [ ] No console errors
- [ ] No console warnings (in production build)
- [ ] Images load efficiently
- [ ] Smooth animations and transitions

### 12. Browser Compatibility

- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari
- [ ] Works in Edge
- [ ] No major layout issues

## 🔧 Development Checks

- [ ] `npm run dev` starts without errors
- [ ] `npm run build` completes successfully
- [ ] `npm run preview` works correctly
- [ ] No ESLint errors
- [ ] All environment variables load correctly
- [ ] No sensitive data in code

## 📝 Code Quality

- [ ] Components are well-structured
- [ ] Code is readable and commented
- [ ] No unused imports
- [ ] No console.log in production code
- [ ] Error handling in all API calls
- [ ] Loading states for all async operations

## 🚀 Production Ready

- [ ] All features tested and working
- [ ] No critical bugs
- [ ] Documentation is complete
- [ ] README is up to date
- [ ] Environment variables documented
- [ ] Build process documented

## 📊 Final Checks

- [ ] All todos completed
- [ ] All test cases passed
- [ ] Ready for demo/presentation
- [ ] Ready for deployment

---

**Total Checks: ~150+**

Use this checklist to thoroughly test the application before deploying or presenting!
