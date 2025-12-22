# E-Com67 Shared Components

Shared components and utilities library for the E-Com67 frontend applications.

## Overview

This library provides reusable components, utilities, and services that are shared between the admin dashboard and customer application. It helps maintain consistency and reduces code duplication across the dual-frontend architecture.

## Components

### Button
Reusable button component with multiple variants and states.

```jsx
import { Button } from '@e-com67/shared'

<Button variant="primary" size="md" loading={false}>
  Click me
</Button>
```

**Props:**
- `variant`: 'primary' | 'secondary' | 'danger' | 'outline'
- `size`: 'sm' | 'md' | 'lg'
- `loading`: boolean
- `disabled`: boolean

### Input
Form input component with label and error handling.

```jsx
import { Input } from '@e-com67/shared'

<Input 
  label="Email" 
  required 
  error={errors.email}
  type="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>
```

**Props:**
- `label`: string
- `error`: string
- `required`: boolean
- All standard HTML input props

### Modal
Modal dialog component with customizable size.

```jsx
import { Modal } from '@e-com67/shared'

<Modal 
  isOpen={showModal} 
  onClose={() => setShowModal(false)}
  title="Confirm Action"
  size="md"
>
  <p>Are you sure you want to continue?</p>
</Modal>
```

**Props:**
- `isOpen`: boolean
- `onClose`: function
- `title`: string
- `size`: 'sm' | 'md' | 'lg' | 'xl'

## Services

### ApiClient
HTTP client with authentication and error handling.

```jsx
import { ApiClient } from '@e-com67/shared'

const api = new ApiClient(
  'https://api.example.com',
  () => getCurrentUserToken()
)

// Usage
const products = await api.get('/products')
const newProduct = await api.post('/products', productData)
```

## Utilities

### Formatters
Common formatting functions for currency, dates, and numbers.

```jsx
import { formatCurrency, formatDate, formatRelativeTime } from '@e-com67/shared'

formatCurrency(29.99) // "$29.99"
formatDate('2024-01-15') // "Jan 15, 2024"
formatRelativeTime('2024-01-15T10:00:00Z') // "2 hours ago"
```

### Validation
Form validation utilities and helpers.

```jsx
import { validateForm, isValidEmail } from '@e-com67/shared'

const { isValid, errors } = validateForm(formData, {
  email: { required: true, email: true },
  password: { required: true, password: true },
  name: { required: true, minLength: 2 }
})
```

## Development

### Building the Library

```bash
npm run build
```

### Development Mode (Watch)

```bash
npm run dev
```

## Usage in Applications

To use this shared library in the admin dashboard or customer app:

1. Install as a local dependency:
```bash
npm install file:../shared
```

2. Import components and utilities:
```jsx
import { Button, Input, Modal, ApiClient, formatCurrency } from '@e-com67/shared'
```

## Design System

The shared components follow a consistent design system:

- **Colors**: Primary blue theme with semantic variants
- **Spacing**: Tailwind CSS spacing scale
- **Typography**: System font stack with proper hierarchy
- **Interactions**: Consistent hover and focus states

## Contributing

When adding new shared components:

1. Keep components simple and focused on a single responsibility
2. Use TypeScript-style prop validation with clear documentation
3. Follow the existing naming conventions
4. Include proper error handling and loading states
5. Test components in both applications before committing

## Architecture

This shared library is part of the E-Com67 dual-frontend architecture:

- **Admin Dashboard** (`frontends/admin-dashboard/`): Administrative interface
- **Customer Application** (`frontends/customer-app/`): Customer shopping experience  
- **Shared Components** (`frontends/shared/`): This library - reusable components

The library is designed to be lightweight and focused on common functionality that both applications need, while allowing each application to maintain its specific features and styling.