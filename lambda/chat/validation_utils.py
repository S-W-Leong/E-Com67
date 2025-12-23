"""
Validation and Sanitization Utilities for Strands AI Agent

This module provides utilities for validating and sanitizing data
before converting to Pydantic models and sending responses.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


# ============================================================================
# Data Validation Functions
# ============================================================================

def validate_product_data(product_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate product data and return validation errors.
    
    Args:
        product_data: Raw product data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required fields validation
    required_fields = ['name', 'price', 'category']
    for field in required_fields:
        if not product_data.get(field):
            errors.setdefault(field, []).append(f"{field} is required")
    
    # Price validation
    price = product_data.get('price')
    if price is not None:
        try:
            price_float = float(price)
            if price_float < 0:
                errors.setdefault('price', []).append("Price must be non-negative")
            if price_float > 1000000:  # Reasonable upper limit
                errors.setdefault('price', []).append("Price exceeds maximum allowed value")
        except (ValueError, TypeError):
            errors.setdefault('price', []).append("Price must be a valid number")
    
    # Stock validation
    stock = product_data.get('stock')
    if stock is not None:
        try:
            stock_int = int(stock)
            if stock_int < 0:
                errors.setdefault('stock', []).append("Stock must be non-negative")
        except (ValueError, TypeError):
            errors.setdefault('stock', []).append("Stock must be a valid integer")
    
    # Rating validation
    rating = product_data.get('rating')
    if rating is not None:
        try:
            rating_float = float(rating)
            if not 0 <= rating_float <= 5:
                errors.setdefault('rating', []).append("Rating must be between 0 and 5")
        except (ValueError, TypeError):
            errors.setdefault('rating', []).append("Rating must be a valid number")
    
    # URL validation
    image_url = product_data.get('imageUrl', product_data.get('image_url'))
    if image_url and not _is_valid_url(image_url):
        errors.setdefault('image_url', []).append("Invalid image URL format")
    
    return errors


def validate_cart_data(cart_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate cart data and return validation errors.
    
    Args:
        cart_data: Raw cart data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required fields validation
    if not cart_data.get('userId', cart_data.get('user_id')):
        errors.setdefault('user_id', []).append("User ID is required")
    
    # Items validation
    items = cart_data.get('items', [])
    if not isinstance(items, list):
        errors.setdefault('items', []).append("Items must be a list")
    else:
        for i, item in enumerate(items):
            item_errors = validate_cart_item_data(item)
            for field, field_errors in item_errors.items():
                errors.setdefault(f'items[{i}].{field}', []).extend(field_errors)
    
    # Monetary values validation
    monetary_fields = ['subtotal', 'tax', 'shipping', 'discount', 'total']
    for field in monetary_fields:
        value = cart_data.get(field)
        if value is not None:
            try:
                value_float = float(value)
                if value_float < 0:
                    errors.setdefault(field, []).append(f"{field} must be non-negative")
            except (ValueError, TypeError):
                errors.setdefault(field, []).append(f"{field} must be a valid number")
    
    return errors


def validate_cart_item_data(item_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate individual cart item data.
    
    Args:
        item_data: Raw cart item data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required fields
    required_fields = ['productId', 'name', 'price', 'quantity']
    for field in required_fields:
        alt_field = field.replace('Id', '_id') if 'Id' in field else field
        if not item_data.get(field) and not item_data.get(alt_field):
            errors.setdefault(field, []).append(f"{field} is required")
    
    # Quantity validation
    quantity = item_data.get('quantity')
    if quantity is not None:
        try:
            quantity_int = int(quantity)
            if quantity_int <= 0:
                errors.setdefault('quantity', []).append("Quantity must be positive")
            if quantity_int > 1000:  # Reasonable upper limit
                errors.setdefault('quantity', []).append("Quantity exceeds maximum allowed")
        except (ValueError, TypeError):
            errors.setdefault('quantity', []).append("Quantity must be a valid integer")
    
    # Price validation
    price = item_data.get('price')
    if price is not None:
        try:
            price_float = float(price)
            if price_float < 0:
                errors.setdefault('price', []).append("Price must be non-negative")
        except (ValueError, TypeError):
            errors.setdefault('price', []).append("Price must be a valid number")
    
    return errors


def validate_order_data(order_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate order data and return validation errors.
    
    Args:
        order_data: Raw order data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required fields validation
    required_fields = ['orderId', 'userId', 'status']
    for field in required_fields:
        alt_field = field.replace('Id', '_id') if 'Id' in field else field
        if not order_data.get(field) and not order_data.get(alt_field):
            errors.setdefault(field, []).append(f"{field} is required")
    
    # Status validation
    status = order_data.get('status')
    if status:
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
        if status.lower() not in valid_statuses:
            errors.setdefault('status', []).append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Items validation
    items = order_data.get('items', [])
    if not isinstance(items, list):
        errors.setdefault('items', []).append("Items must be a list")
    elif len(items) == 0:
        errors.setdefault('items', []).append("Order must contain at least one item")
    else:
        for i, item in enumerate(items):
            item_errors = validate_order_item_data(item)
            for field, field_errors in item_errors.items():
                errors.setdefault(f'items[{i}].{field}', []).extend(field_errors)
    
    # Monetary values validation
    monetary_fields = ['subtotal', 'tax', 'shipping', 'discount', 'totalAmount', 'total_amount']
    for field in monetary_fields:
        value = order_data.get(field)
        if value is not None:
            try:
                value_float = float(value)
                if value_float < 0:
                    errors.setdefault(field, []).append(f"{field} must be non-negative")
            except (ValueError, TypeError):
                errors.setdefault(field, []).append(f"{field} must be a valid number")
    
    # Address validation
    shipping_address = order_data.get('shippingAddress', order_data.get('shipping_address'))
    if shipping_address:
        address_errors = validate_address_data(shipping_address)
        for field, field_errors in address_errors.items():
            errors.setdefault(f'shipping_address.{field}', []).extend(field_errors)
    
    return errors


def validate_order_item_data(item_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate individual order item data.
    
    Args:
        item_data: Raw order item data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required fields
    required_fields = ['productId', 'name', 'price', 'quantity']
    for field in required_fields:
        alt_field = field.replace('Id', '_id') if 'Id' in field else field
        if not item_data.get(field) and not item_data.get(alt_field):
            errors.setdefault(field, []).append(f"{field} is required")
    
    # Quantity validation (same as cart item)
    quantity = item_data.get('quantity')
    if quantity is not None:
        try:
            quantity_int = int(quantity)
            if quantity_int <= 0:
                errors.setdefault('quantity', []).append("Quantity must be positive")
        except (ValueError, TypeError):
            errors.setdefault('quantity', []).append("Quantity must be a valid integer")
    
    # Price validation (same as cart item)
    price = item_data.get('price')
    if price is not None:
        try:
            price_float = float(price)
            if price_float < 0:
                errors.setdefault('price', []).append("Price must be non-negative")
        except (ValueError, TypeError):
            errors.setdefault('price', []).append("Price must be a valid number")
    
    return errors


def validate_address_data(address_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate address data.
    
    Args:
        address_data: Raw address data to validate
        
    Returns:
        Dict containing validation errors by field
    """
    errors = {}
    
    # Required address fields
    required_fields = ['street', 'city', 'country']
    for field in required_fields:
        if not address_data.get(field):
            errors.setdefault(field, []).append(f"{field} is required")
    
    # Postal code validation (basic)
    postal_code = address_data.get('postalCode', address_data.get('postal_code', address_data.get('zip')))
    if postal_code and not _is_valid_postal_code(postal_code):
        errors.setdefault('postal_code', []).append("Invalid postal code format")
    
    return errors


# ============================================================================
# Data Sanitization Functions
# ============================================================================

def sanitize_product_data(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize product data by cleaning and normalizing values.
    
    Args:
        product_data: Raw product data to sanitize
        
    Returns:
        Dict containing sanitized product data
    """
    sanitized = {}
    
    # Clean string fields
    string_fields = ['name', 'description', 'category', 'brand', 'sku']
    for field in string_fields:
        value = product_data.get(field)
        if value:
            sanitized[field] = _sanitize_string(str(value))
    
    # Handle numeric fields
    price = product_data.get('price')
    if price is not None:
        sanitized['price'] = _sanitize_decimal(price)
    
    stock = product_data.get('stock')
    if stock is not None:
        sanitized['stock'] = _sanitize_integer(stock)
    
    rating = product_data.get('rating')
    if rating is not None:
        sanitized['rating'] = _sanitize_decimal(rating)
    
    # Handle boolean fields
    is_available = product_data.get('isAvailable', product_data.get('is_available'))
    if is_available is not None:
        sanitized['is_available'] = bool(is_available)
    
    # Handle arrays
    tags = product_data.get('tags')
    if tags and isinstance(tags, list):
        sanitized['tags'] = [_sanitize_string(str(tag)) for tag in tags if tag]
    
    # Handle URLs
    image_url = product_data.get('imageUrl', product_data.get('image_url'))
    if image_url:
        sanitized['image_url'] = _sanitize_url(str(image_url))
    
    # Copy other fields as-is
    for field in ['productId', 'product_id', 'currency', 'specifications']:
        if field in product_data:
            sanitized[field] = product_data[field]
    
    return sanitized


def sanitize_cart_data(cart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize cart data by cleaning and normalizing values.
    
    Args:
        cart_data: Raw cart data to sanitize
        
    Returns:
        Dict containing sanitized cart data
    """
    sanitized = {}
    
    # Copy user ID
    user_id = cart_data.get('userId', cart_data.get('user_id'))
    if user_id:
        sanitized['user_id'] = _sanitize_string(str(user_id))
    
    # Sanitize items
    items = cart_data.get('items', [])
    if isinstance(items, list):
        sanitized['items'] = [sanitize_cart_item_data(item) for item in items]
    
    # Handle monetary values
    monetary_fields = ['subtotal', 'tax', 'shipping', 'discount', 'total']
    for field in monetary_fields:
        value = cart_data.get(field)
        if value is not None:
            sanitized[field] = _sanitize_decimal(value)
    
    # Handle other fields
    for field in ['currency', 'lastUpdated', 'last_updated', 'isValid', 'is_valid', 'validationErrors', 'validation_errors']:
        if field in cart_data:
            sanitized[field] = cart_data[field]
    
    return sanitized


def sanitize_cart_item_data(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize individual cart item data.
    
    Args:
        item_data: Raw cart item data to sanitize
        
    Returns:
        Dict containing sanitized cart item data
    """
    sanitized = {}
    
    # Handle string fields
    for field in ['productId', 'product_id', 'name', 'category', 'sku']:
        value = item_data.get(field)
        if value:
            sanitized[field] = _sanitize_string(str(value))
    
    # Handle numeric fields
    price = item_data.get('price')
    if price is not None:
        sanitized['price'] = _sanitize_decimal(price)
    
    quantity = item_data.get('quantity')
    if quantity is not None:
        sanitized['quantity'] = _sanitize_integer(quantity)
    
    subtotal = item_data.get('subtotal')
    if subtotal is not None:
        sanitized['subtotal'] = _sanitize_decimal(subtotal)
    
    stock_quantity = item_data.get('stockQuantity', item_data.get('stock_quantity', item_data.get('stock')))
    if stock_quantity is not None:
        sanitized['stock_quantity'] = _sanitize_integer(stock_quantity)
    
    # Handle boolean fields
    is_available = item_data.get('isAvailable', item_data.get('is_available'))
    if is_available is not None:
        sanitized['is_available'] = bool(is_available)
    
    # Handle URLs
    image_url = item_data.get('imageUrl', item_data.get('image_url'))
    if image_url:
        sanitized['image_url'] = _sanitize_url(str(image_url))
    
    # Handle timestamps
    added_at = item_data.get('addedAt', item_data.get('added_at'))
    if added_at:
        sanitized['added_at'] = added_at
    
    return sanitized


def sanitize_order_data(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize order data by cleaning and normalizing values.
    
    Args:
        order_data: Raw order data to sanitize
        
    Returns:
        Dict containing sanitized order data
    """
    sanitized = {}
    
    # Handle string fields
    string_fields = ['orderId', 'order_id', 'userId', 'user_id', 'status', 'paymentMethod', 'payment_method', 'paymentStatus', 'payment_status']
    for field in string_fields:
        value = order_data.get(field)
        if value:
            sanitized[field] = _sanitize_string(str(value))
    
    # Sanitize items
    items = order_data.get('items', [])
    if isinstance(items, list):
        sanitized['items'] = [sanitize_order_item_data(item) for item in items]
    
    # Handle monetary values
    monetary_fields = ['subtotal', 'tax', 'shipping', 'discount', 'totalAmount', 'total_amount']
    for field in monetary_fields:
        value = order_data.get(field)
        if value is not None:
            sanitized[field] = _sanitize_decimal(value)
    
    # Handle addresses
    shipping_address = order_data.get('shippingAddress', order_data.get('shipping_address'))
    if shipping_address and isinstance(shipping_address, dict):
        sanitized['shipping_address'] = sanitize_address_data(shipping_address)
    
    billing_address = order_data.get('billingAddress', order_data.get('billing_address'))
    if billing_address and isinstance(billing_address, dict):
        sanitized['billing_address'] = sanitize_address_data(billing_address)
    
    # Handle other fields
    for field in ['currency', 'orderDate', 'order_date', 'estimatedDelivery', 'estimated_delivery', 'actualDelivery', 'actual_delivery', 'trackingNumber', 'tracking_number']:
        if field in order_data:
            sanitized[field] = order_data[field]
    
    return sanitized


def sanitize_order_item_data(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize individual order item data.
    
    Args:
        item_data: Raw order item data to sanitize
        
    Returns:
        Dict containing sanitized order item data
    """
    sanitized = {}
    
    # Handle string fields
    for field in ['productId', 'product_id', 'name', 'category', 'sku']:
        value = item_data.get(field)
        if value:
            sanitized[field] = _sanitize_string(str(value))
    
    # Handle numeric fields
    price = item_data.get('price')
    if price is not None:
        sanitized['price'] = _sanitize_decimal(price)
    
    quantity = item_data.get('quantity')
    if quantity is not None:
        sanitized['quantity'] = _sanitize_integer(quantity)
    
    subtotal = item_data.get('subtotal')
    if subtotal is not None:
        sanitized['subtotal'] = _sanitize_decimal(subtotal)
    
    return sanitized


def sanitize_address_data(address_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize address data by cleaning and normalizing values.
    
    Args:
        address_data: Raw address data to sanitize
        
    Returns:
        Dict containing sanitized address data
    """
    sanitized = {}
    
    # Handle string fields
    string_fields = ['street', 'city', 'state', 'country', 'postalCode', 'postal_code', 'zip']
    for field in string_fields:
        value = address_data.get(field)
        if value:
            sanitized[field] = _sanitize_string(str(value))
    
    return sanitized


# ============================================================================
# Helper Functions
# ============================================================================

def _sanitize_string(value: str) -> str:
    """Sanitize string by trimming and removing dangerous characters."""
    if not isinstance(value, str):
        value = str(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Remove null bytes and control characters
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    
    # Limit length to prevent abuse
    if len(value) > 1000:
        value = value[:1000]
    
    return value


def _sanitize_decimal(value: Union[str, int, float, Decimal]) -> float:
    """Sanitize decimal value and convert to float."""
    try:
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Remove any non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d.-]', '', value)
            return float(cleaned) if cleaned else 0.0
        else:
            return 0.0
    except (ValueError, InvalidOperation):
        return 0.0


def _sanitize_integer(value: Union[str, int, float]) -> int:
    """Sanitize integer value."""
    try:
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            # Remove any non-numeric characters except minus
            cleaned = re.sub(r'[^\d-]', '', value)
            return int(cleaned) if cleaned else 0
        else:
            return 0
    except ValueError:
        return 0


def _sanitize_url(value: str) -> str:
    """Sanitize URL value."""
    if not isinstance(value, str):
        value = str(value)
    
    # Basic URL sanitization
    value = value.strip()
    
    # Ensure it starts with http:// or https://
    if value and not value.startswith(('http://', 'https://')):
        if value.startswith('//'):
            value = 'https:' + value
        elif not value.startswith('/'):
            value = 'https://' + value
    
    return value


def _is_valid_url(url: str) -> bool:
    """Check if URL has valid format."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def _is_valid_postal_code(postal_code: str) -> bool:
    """Check if postal code has valid format (basic validation)."""
    # Basic validation - alphanumeric with optional spaces and hyphens
    postal_pattern = re.compile(r'^[A-Z0-9\s-]{3,10}$', re.IGNORECASE)
    return postal_pattern.match(postal_code.strip()) is not None


# ============================================================================
# Batch Validation Functions
# ============================================================================

def validate_and_sanitize_products(products_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate and sanitize a list of products.
    
    Args:
        products_data: List of raw product data
        
    Returns:
        Tuple of (valid_products, invalid_products_with_errors)
    """
    valid_products = []
    invalid_products = []
    
    for i, product in enumerate(products_data):
        try:
            # Validate first
            errors = validate_product_data(product)
            if errors:
                invalid_products.append({
                    'index': i,
                    'data': product,
                    'errors': errors
                })
                continue
            
            # Sanitize if valid
            sanitized = sanitize_product_data(product)
            valid_products.append(sanitized)
            
        except Exception as e:
            logger.error(f"Error processing product at index {i}: {str(e)}")
            invalid_products.append({
                'index': i,
                'data': product,
                'errors': {'general': [f"Processing error: {str(e)}"]}
            })
    
    return valid_products, invalid_products


def validate_and_sanitize_orders(orders_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate and sanitize a list of orders.
    
    Args:
        orders_data: List of raw order data
        
    Returns:
        Tuple of (valid_orders, invalid_orders_with_errors)
    """
    valid_orders = []
    invalid_orders = []
    
    for i, order in enumerate(orders_data):
        try:
            # Validate first
            errors = validate_order_data(order)
            if errors:
                invalid_orders.append({
                    'index': i,
                    'data': order,
                    'errors': errors
                })
                continue
            
            # Sanitize if valid
            sanitized = sanitize_order_data(order)
            valid_orders.append(sanitized)
            
        except Exception as e:
            logger.error(f"Error processing order at index {i}: {str(e)}")
            invalid_orders.append({
                'index': i,
                'data': order,
                'errors': {'general': [f"Processing error: {str(e)}"]}
            })
    
    return valid_orders, invalid_orders