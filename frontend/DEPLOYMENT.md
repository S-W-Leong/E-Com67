# E-Com67 Frontend - Deployment Guide

## 🎯 Deployment Options

### Option 1: AWS S3 + CloudFront (Recommended)
Best for: Production deployment with CDN

### Option 2: AWS Amplify Hosting
Best for: Quick deployment with CI/CD

### Option 3: Vercel/Netlify
Best for: Quick deployment with automatic builds

---

## 📦 Option 1: AWS S3 + CloudFront

### Prerequisites
- AWS CLI configured
- S3 bucket created
- CloudFront distribution (optional but recommended)

### Step 1: Build the Application

```bash
cd frontend
npm run build
```

This creates a `dist/` directory with optimized production files.

### Step 2: Create S3 Bucket (if not exists)

```bash
# Create bucket
aws s3 mb s3://e-com67-frontend-prod --region ap-southeast-1

# Enable static website hosting
aws s3 website s3://e-com67-frontend-prod \
  --index-document index.html \
  --error-document index.html
```

### Step 3: Configure Bucket Policy

Create `bucket-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::e-com67-frontend-prod/*"
    }
  ]
}
```

Apply policy:

```bash
aws s3api put-bucket-policy \
  --bucket e-com67-frontend-prod \
  --policy file://bucket-policy.json
```

### Step 4: Deploy to S3

```bash
# Deploy files
aws s3 sync dist/ s3://e-com67-frontend-prod --delete

# Set correct content types
aws s3 cp dist/ s3://e-com67-frontend-prod --recursive \
  --exclude "*" --include "*.html" --content-type "text/html; charset=utf-8" \
  --metadata-directive REPLACE

aws s3 cp dist/ s3://e-com67-frontend-prod --recursive \
  --exclude "*" --include "*.js" --content-type "application/javascript; charset=utf-8" \
  --metadata-directive REPLACE

aws s3 cp dist/ s3://e-com67-frontend-prod --recursive \
  --exclude "*" --include "*.css" --content-type "text/css; charset=utf-8" \
  --metadata-directive REPLACE
```

### Step 5: Create CloudFront Distribution (Optional but Recommended)

```bash
# Create distribution
aws cloudfront create-distribution \
  --origin-domain-name e-com67-frontend-prod.s3-website-ap-southeast-1.amazonaws.com \
  --default-root-object index.html
```

Or use AWS Console:
1. Go to CloudFront
2. Create Distribution
3. Origin Domain: Your S3 bucket
4. Viewer Protocol Policy: Redirect HTTP to HTTPS
5. Default Root Object: `index.html`
6. Custom Error Pages: 404 → /index.html (for SPA routing)

### Step 6: Update Environment Variables

If using CloudFront, update your frontend to use the CloudFront URL.

### Website URL

- **S3 Direct**: `http://e-com67-frontend-prod.s3-website-ap-southeast-1.amazonaws.com`
- **CloudFront**: `https://d123456789.cloudfront.net` (or custom domain)

---

## 🚀 Option 2: AWS Amplify Hosting

### Step 1: Initialize Amplify

```bash
cd frontend
npm install -g @aws-amplify/cli
amplify init
```

### Step 2: Add Hosting

```bash
amplify add hosting

# Choose:
# - Hosting with Amplify Console (Managed hosting)
# - Continuous deployment
```

### Step 3: Deploy

```bash
amplify publish
```

### Step 4: Environment Variables

Add environment variables in Amplify Console:
1. Go to Amplify Console
2. Select your app
3. Environment variables
4. Add all `VITE_*` variables

### Benefits
- Automatic CI/CD
- Branch deployments
- Free SSL certificate
- Global CDN

---

## 🌐 Option 3: Vercel

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy

```bash
cd frontend
vercel
```

### Step 3: Configure Environment Variables

```bash
vercel env add VITE_AWS_REGION
vercel env add VITE_API_GATEWAY_ENDPOINT
vercel env add VITE_COGNITO_USER_POOL_ID
vercel env add VITE_COGNITO_APP_CLIENT_ID
```

Or add them in the Vercel dashboard.

### Step 4: Production Deployment

```bash
vercel --prod
```

---

## 🔧 Deployment Script

Create `deploy.sh` in frontend directory:

```bash
#!/bin/bash

# E-Com67 Frontend Deployment Script

set -e

echo "🚀 E-Com67 Frontend Deployment"
echo "==============================="

# Configuration
BUCKET_NAME="e-com67-frontend-prod"
REGION="ap-southeast-1"
CLOUDFRONT_ID="E1234567890ABC"  # Replace with your CloudFront ID

# Build
echo "📦 Building application..."
npm run build

# Deploy to S3
echo "☁️  Deploying to S3..."
aws s3 sync dist/ s3://$BUCKET_NAME \
  --region $REGION \
  --delete \
  --cache-control "public,max-age=31536000,immutable"

# Update index.html with no-cache
echo "🔄 Updating index.html..."
aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html \
  --region $REGION \
  --cache-control "public,max-age=0,must-revalidate" \
  --metadata-directive REPLACE

# Invalidate CloudFront (if using)
if [ ! -z "$CLOUDFRONT_ID" ]; then
  echo "🔃 Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_ID \
    --paths "/*"
fi

echo "✅ Deployment complete!"
echo "🌐 Website: https://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
```

Make it executable:

```bash
chmod +x deploy.sh
```

Run deployment:

```bash
./deploy.sh
```

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Remove all `console.log` statements
- [ ] Enable HTTPS only (CloudFront)
- [ ] Set up CORS properly on API Gateway
- [ ] Use environment-specific configs
- [ ] Enable CloudFront WAF (optional)
- [ ] Set up monitoring (CloudWatch)
- [ ] Configure proper cache headers
- [ ] Add security headers

### Security Headers

Add to CloudFront or S3:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
```

---

## 📊 Monitoring & Analytics

### CloudWatch Monitoring

Monitor:
- S3 bucket metrics
- CloudFront metrics
- Error rates
- Bandwidth usage

### Add Google Analytics (Optional)

1. Create GA4 property
2. Add to `index.html`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to S3

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Build
        run: |
          cd frontend
          npm run build
        env:
          VITE_AWS_REGION: ${{ secrets.VITE_AWS_REGION }}
          VITE_API_GATEWAY_ENDPOINT: ${{ secrets.VITE_API_GATEWAY_ENDPOINT }}
          VITE_COGNITO_USER_POOL_ID: ${{ secrets.VITE_COGNITO_USER_POOL_ID }}
          VITE_COGNITO_APP_CLIENT_ID: ${{ secrets.VITE_COGNITO_APP_CLIENT_ID }}

      - name: Deploy to S3
        uses: jakejarvis/s3-sync-action@master
        with:
          args: --delete
        env:
          AWS_S3_BUCKET: e-com67-frontend-prod
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ap-southeast-1
          SOURCE_DIR: frontend/dist

      - name: Invalidate CloudFront
        uses: chetan/invalidate-cloudfront-action@v2
        env:
          DISTRIBUTION: ${{ secrets.CLOUDFRONT_ID }}
          PATHS: '/*'
          AWS_REGION: ap-southeast-1
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

Add secrets in GitHub:
- `VITE_AWS_REGION`
- `VITE_API_GATEWAY_ENDPOINT`
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_APP_CLIENT_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `CLOUDFRONT_ID`

---

## 🐛 Troubleshooting Deployment

### Issue: 404 on Refresh

**Solution**: Configure CloudFront Custom Error Responses:
- Error Code: 404
- Response Page Path: `/index.html`
- HTTP Response Code: 200

### Issue: Old Files Cached

**Solution**: Invalidate CloudFront cache:

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Issue: Environment Variables Not Working

**Solution**:
- Ensure variables have `VITE_` prefix
- Rebuild after changing variables
- Check `vite.config.js` loads them correctly

### Issue: CORS Errors

**Solution**:
- Check API Gateway CORS settings
- Ensure backend allows your domain
- Check browser console for exact error

---

## 📈 Performance Optimization

### 1. Enable Gzip/Brotli Compression

CloudFront does this automatically.

### 2. Optimize Images

```bash
# Install sharp
npm install sharp

# Create optimization script
# Add to package.json scripts
```

### 3. Code Splitting

Already handled by Vite with React Router.

### 4. Lazy Loading

Add lazy loading to routes:

```javascript
const Products = lazy(() => import('./pages/Products'));
```

---

## ✅ Post-Deployment Checklist

- [ ] Website loads correctly
- [ ] Login/signup works
- [ ] All API calls work
- [ ] Images load
- [ ] No console errors
- [ ] HTTPS enabled
- [ ] Custom domain configured (if applicable)
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] Team has access

---

## 🌟 Production URL

After deployment, your app will be available at:

- **S3**: `http://e-com67-frontend-prod.s3-website-ap-southeast-1.amazonaws.com`
- **CloudFront**: `https://d123456789.cloudfront.net`
- **Custom Domain**: `https://yourdomain.com` (if configured)

---

**Need help? Check the troubleshooting section or review AWS documentation.**
