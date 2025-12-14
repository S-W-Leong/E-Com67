"""Shared type definitions and models."""

from typing import TypedDict, Optional, List

class Product(TypedDict):
    """Product model."""
    productId: str
    name: str
    description: str
    price: float
    category: str
    stock: int
    imageUrl: Optional[str]

class CartItem(TypedDict):
    """Cart item model."""
    userId: str
    productId: str
    name: str
    price: float
    quantity: int

class Order(TypedDict):
    """Order model."""
    orderId: str
    userId: str
    items: List[CartItem]
    totalAmount: float
    status: str
    paymentId: str
    timestamp: float

class User(TypedDict):
    """User model."""
    userId: str
    email: str
    createdAt: float
    lastLogin: Optional[float]

class ApiResponse(TypedDict):
    """Standard API response model."""
    statusCode: int
    body: str
    headers: dict
