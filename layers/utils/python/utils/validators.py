"""
Validation utilities for E-Com67 platform
"""

import re
from typing import Dict, Any
from .exceptions import ValidationError


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_product_data(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate product data structure and values"""
    required_fields = ['name', 'description', 'price', 'category']
    
    for field in required_fields:
        if field not in product_data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate price
    try:
        price = float(product_data['price'])
        if price < 0:
            raise ValidationError("Price must be non-negative")
        product_data['price'] = price
    except (ValueError, TypeError):
        raise ValidationError("Price must be a valid number")
    
    # Validate stock if provided
    if 'stock' in product_data:
        try:
            stock = int(product_data['stock'])
            if stock < 0:
                raise ValidationError("Stock must be non-negative")
            product_data['stock'] = stock
        except (ValueError, TypeError):
            raise ValidationError("Stock must be a valid integer")
    
    return product_data


def validate_cart_item(cart_item: Dict[str, Any]) -> Dict[str, Any]:
    """Validate cart item data"""
    required_fields = ['productId', 'quantity']
    
    for field in required_fields:
        if field not in cart_item:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate quantity
    try:
        quantity = int(cart_item['quantity'])
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        cart_item['quantity'] = quantity
    except (ValueError, TypeError):
        raise ValidationError("Quantity must be a valid positive integer")
    
    return cart_item