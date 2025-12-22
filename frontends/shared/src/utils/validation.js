// Email validation
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Password validation
export const isValidPassword = (password) => {
  // At least 8 characters, 1 uppercase, 1 lowercase, 1 number
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/
  return passwordRegex.test(password)
}

// Required field validation
export const isRequired = (value) => {
  return value !== null && value !== undefined && value.toString().trim() !== ''
}

// Price validation
export const isValidPrice = (price) => {
  const priceRegex = /^\d+(\.\d{1,2})?$/
  return priceRegex.test(price) && parseFloat(price) > 0
}

// Phone number validation (basic)
export const isValidPhone = (phone) => {
  const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/
  return phoneRegex.test(phone)
}

// Form validation helper
export const validateForm = (data, rules) => {
  const errors = {}
  
  Object.keys(rules).forEach(field => {
    const value = data[field]
    const fieldRules = rules[field]
    
    if (fieldRules.required && !isRequired(value)) {
      errors[field] = `${field} is required`
      return
    }
    
    if (value && fieldRules.email && !isValidEmail(value)) {
      errors[field] = 'Please enter a valid email address'
      return
    }
    
    if (value && fieldRules.password && !isValidPassword(value)) {
      errors[field] = 'Password must be at least 8 characters with uppercase, lowercase, and number'
      return
    }
    
    if (value && fieldRules.price && !isValidPrice(value)) {
      errors[field] = 'Please enter a valid price'
      return
    }
    
    if (value && fieldRules.phone && !isValidPhone(value)) {
      errors[field] = 'Please enter a valid phone number'
      return
    }
    
    if (value && fieldRules.minLength && value.length < fieldRules.minLength) {
      errors[field] = `${field} must be at least ${fieldRules.minLength} characters`
      return
    }
    
    if (value && fieldRules.maxLength && value.length > fieldRules.maxLength) {
      errors[field] = `${field} must be no more than ${fieldRules.maxLength} characters`
      return
    }
  })
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  }
}