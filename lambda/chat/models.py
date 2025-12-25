"""
Pydantic Models for Strands AI Agent Structured Responses

This module defines comprehensive Pydantic models for structured responses
in the E-Com67 Strands AI Agent enhancement. These models ensure consistent
data formatting across all agent interactions and tool operations.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


# ============================================================================
# Product Models
# ============================================================================

class ProductInfo(BaseModel):
    """Comprehensive product information model"""
    product_id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., ge=0, description="Product price")
    currency: str = Field(default="USD", description="Price currency")
    category: str = Field(..., description="Product category")
    stock: int = Field(..., ge=0, description="Available stock quantity")
    image_url: Optional[str] = Field(None, description="Product image URL")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating")
    tags: List[str] = Field(default_factory=list, description="Product tags")
    is_available: bool = Field(..., description="Product availability status")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Product specifications")
    brand: Optional[str] = Field(None, description="Product brand")
    sku: Optional[str] = Field(None, description="Stock keeping unit")
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Price must be non-negative')
        return round(v, 2)

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v


class ProductRecommendation(BaseModel):
    """Product recommendation with reasoning and scoring"""
    product: ProductInfo
    relevance_score: float = Field(..., ge=0, le=1, description="Recommendation relevance")
    reasoning: str = Field(..., description="Why this product is recommended")
    category_match: bool = Field(..., description="Whether category matches user query")
    price_match: bool = Field(..., description="Whether price is within user range")
    similarity_factors: List[str] = Field(default_factory=list, description="Factors contributing to similarity")
    confidence_level: str = Field(default="medium", description="Confidence level (low, medium, high)")
    
    @field_validator('relevance_score')
    @classmethod
    def validate_relevance_score(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError('Relevance score must be between 0 and 1')
        return round(v, 3)


class ProductSearchResponse(BaseModel):
    """Comprehensive product search response"""
    query: str = Field(..., description="Original search query")
    products: List[ProductInfo] = Field(..., description="Matching products")
    recommendations: List[ProductRecommendation] = Field(default_factory=list)
    total_count: int = Field(..., ge=0, description="Total matching products")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    suggestions: List[str] = Field(default_factory=list, description="Alternative search suggestions")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied search filters")
    search_time_ms: Optional[int] = Field(None, description="Search execution time in milliseconds")
    has_more: bool = Field(default=False, description="Whether more results are available")
    
    @field_validator('total_count')
    @classmethod
    def validate_total_count(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Total count must be non-negative')
        return v


# ============================================================================
# Cart Models
# ============================================================================

class CartItem(BaseModel):
    """Individual cart item with validation"""
    product_id: str = Field(..., description="Product identifier")
    name: str = Field(..., description="Product name")
    price: float = Field(..., ge=0, description="Unit price")
    quantity: int = Field(..., ge=1, description="Item quantity")
    subtotal: float = Field(..., ge=0, description="Item subtotal")
    image_url: Optional[str] = Field(None, description="Product image URL")
    is_available: bool = Field(..., description="Current availability")
    stock_quantity: int = Field(..., ge=0, description="Available stock")
    category: Optional[str] = Field(None, description="Product category")
    sku: Optional[str] = Field(None, description="Stock keeping unit")
    added_at: datetime = Field(default_factory=datetime.utcnow, description="When item was added")
    
    @model_validator(mode='after')
    def validate_cart_item(self):
        # Validate subtotal matches price * quantity
        expected_subtotal = round(self.price * self.quantity, 2)
        if abs(self.subtotal - expected_subtotal) > 0.01:
            raise ValueError(f'Subtotal {self.subtotal} does not match price * quantity {expected_subtotal}')
        self.subtotal = round(self.subtotal, 2)

        # Validate quantity against stock
        if self.quantity > self.stock_quantity:
            raise ValueError(f'Requested quantity {self.quantity} exceeds available stock {self.stock_quantity}')
        return self


class CartSummary(BaseModel):
    """Complete cart summary with totals and validation"""
    user_id: str = Field(..., description="User identifier")
    items: List[CartItem] = Field(..., description="Cart items")
    total_items: int = Field(..., ge=0, description="Total number of items")
    subtotal: float = Field(..., ge=0, description="Subtotal before tax")
    tax: float = Field(..., ge=0, description="Tax amount")
    shipping: float = Field(default=0, ge=0, description="Shipping cost")
    discount: float = Field(default=0, ge=0, description="Discount amount")
    total: float = Field(..., ge=0, description="Total amount")
    currency: str = Field(default="USD", description="Currency code")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = Field(..., description="Whether cart is valid for checkout")
    validation_errors: List[str] = Field(default_factory=list)
    estimated_delivery: Optional[datetime] = Field(None, description="Estimated delivery date")
    
    @model_validator(mode='after')
    def validate_cart_summary(self):
        # Validate total_items matches sum of item quantities
        calculated_total = sum(item.quantity for item in self.items)
        if self.total_items != calculated_total:
            raise ValueError(f'Total items {self.total_items} does not match sum of item quantities {calculated_total}')

        # Validate total calculation
        expected_total = self.subtotal + self.tax + self.shipping - self.discount
        if abs(self.total - expected_total) > 0.01:
            raise ValueError(f'Total {self.total} does not match calculated total {expected_total}')
        self.total = round(self.total, 2)
        return self


class CartOperationType(str, Enum):
    """Cart operation types"""
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    CLEAR = "clear"


class CartOperation(BaseModel):
    """Cart operation result with updated state"""
    operation: CartOperationType = Field(..., description="Operation type")
    product_id: Optional[str] = Field(None, description="Target product ID")
    quantity: Optional[int] = Field(None, description="New quantity (for add/update)")
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    cart_summary: CartSummary = Field(..., description="Updated cart state")
    operation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @model_validator(mode='after')
    def validate_quantity_for_operation(self):
        if self.operation in [CartOperationType.ADD, CartOperationType.UPDATE]:
            if self.quantity is None or self.quantity <= 0:
                raise ValueError(f'Quantity must be positive for {self.operation} operations')
        return self


# ============================================================================
# Order Models
# ============================================================================

class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderItem(BaseModel):
    """Individual order item"""
    product_id: str = Field(..., description="Product identifier")
    name: str = Field(..., description="Product name")
    price: float = Field(..., ge=0, description="Unit price at time of order")
    quantity: int = Field(..., ge=1, description="Ordered quantity")
    subtotal: float = Field(..., ge=0, description="Item subtotal")
    sku: Optional[str] = Field(None, description="Stock keeping unit")
    category: Optional[str] = Field(None, description="Product category")
    
    @model_validator(mode='after')
    def validate_item_subtotal(self):
        expected_subtotal = round(self.price * self.quantity, 2)
        if abs(self.subtotal - expected_subtotal) > 0.01:
            raise ValueError(f'Item subtotal {self.subtotal} does not match price * quantity {expected_subtotal}')
        self.subtotal = round(self.subtotal, 2)
        return self


class OrderInfo(BaseModel):
    """Comprehensive order information"""
    order_id: str = Field(..., description="Unique order identifier")
    user_id: str = Field(..., description="User identifier")
    status: OrderStatus = Field(..., description="Current order status")
    items: List[OrderItem] = Field(..., description="Ordered items")
    subtotal: float = Field(..., ge=0, description="Order subtotal")
    tax: float = Field(..., ge=0, description="Tax amount")
    shipping: float = Field(..., ge=0, description="Shipping cost")
    discount: float = Field(default=0, ge=0, description="Discount amount")
    total_amount: float = Field(..., ge=0, description="Total order amount")
    currency: str = Field(default="USD", description="Currency code")
    order_date: datetime = Field(..., description="Order creation date")
    estimated_delivery: Optional[datetime] = Field(None, description="Estimated delivery date")
    actual_delivery: Optional[datetime] = Field(None, description="Actual delivery date")
    tracking_number: Optional[str] = Field(None, description="Shipping tracking number")
    shipping_address: Dict[str, str] = Field(..., description="Shipping address")
    billing_address: Optional[Dict[str, str]] = Field(None, description="Billing address")
    payment_method: str = Field(..., description="Payment method used")
    payment_status: str = Field(default="pending", description="Payment status")
    
    @model_validator(mode='after')
    def validate_order_total(self):
        expected_total = self.subtotal + self.tax + self.shipping - self.discount
        if abs(self.total_amount - expected_total) > 0.01:
            raise ValueError(f'Total amount {self.total_amount} does not match calculated total {expected_total}')
        self.total_amount = round(self.total_amount, 2)
        return self


class OrderHistory(BaseModel):
    """User order history with pagination"""
    user_id: str = Field(..., description="User identifier")
    orders: List[OrderInfo] = Field(..., description="User's orders")
    total_orders: int = Field(..., ge=0, description="Total number of orders")
    page: int = Field(default=1, ge=1, description="Current page")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")
    total_spent: float = Field(default=0, ge=0, description="Total amount spent by user")
    
    @model_validator(mode='after')
    def validate_total_orders(self):
        if len(self.orders) > self.total_orders:
            raise ValueError('Number of orders in list cannot exceed total_orders')
        return self


class OrderStatusUpdate(BaseModel):
    """Order status update information"""
    status: OrderStatus = Field(..., description="New order status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, description="Status update notes")
    location: Optional[str] = Field(None, description="Current location (for shipping)")


class OrderTracking(BaseModel):
    """Order tracking information"""
    order_id: str = Field(..., description="Order identifier")
    current_status: OrderStatus = Field(..., description="Current order status")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    estimated_delivery: Optional[datetime] = Field(None, description="Estimated delivery")
    actual_delivery: Optional[datetime] = Field(None, description="Actual delivery date")
    status_history: List[OrderStatusUpdate] = Field(default_factory=list, description="Status change history")
    carrier: Optional[str] = Field(None, description="Shipping carrier")
    tracking_url: Optional[str] = Field(None, description="Carrier tracking URL")
    current_location: Optional[str] = Field(None, description="Current package location")


# ============================================================================
# Agent Response Models
# ============================================================================

class ResponseType(str, Enum):
    """Agent response types"""
    INFO = "info"
    PRODUCT_LIST = "product_list"
    PRODUCT_DETAIL = "product_detail"
    CART_UPDATE = "cart_update"
    ORDER_INFO = "order_info"
    ERROR = "error"
    CONFIRMATION = "confirmation"
    RECOMMENDATION = "recommendation"


class AgentResponse(BaseModel):
    """Structured agent response"""
    message: str = Field(..., description="Main response message")
    response_type: ResponseType = Field(..., description="Type of response")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data payload")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    tools_used: List[str] = Field(default_factory=list, description="Tools used in processing")
    session_id: str = Field(..., description="Conversation session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requires_action: bool = Field(default=False, description="Whether user action is required")
    action_buttons: List[Dict[str, str]] = Field(default_factory=list, description="Suggested action buttons")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Response confidence")
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v


class ErrorType(str, Enum):
    """Error type classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    RATE_LIMIT = "rate_limit"


class ErrorResponse(BaseModel):
    """Structured error response"""
    error_code: str = Field(..., description="Error code identifier")
    error_message: str = Field(..., description="Human-readable error message")
    error_type: ErrorType = Field(..., description="Error category")
    suggestions: List[str] = Field(default_factory=list, description="Suggested solutions")
    retry_possible: bool = Field(default=True, description="Whether operation can be retried")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    debug_info: Optional[Dict[str, Any]] = Field(None, exclude=True, description="Debug information")


class ToolResult(BaseModel):
    """Tool execution result"""
    tool_name: str = Field(..., description="Name of the tool used")
    success: bool = Field(..., description="Tool execution success")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Tool execution time in seconds")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    
    @field_validator('execution_time')
    @classmethod
    def validate_execution_time(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Execution time must be non-negative')
        return round(v, 3)


# ============================================================================
# Knowledge Base Models
# ============================================================================

class KnowledgeSource(BaseModel):
    """Knowledge base source information"""
    source_id: str = Field(..., description="Source identifier")
    title: str = Field(..., description="Source title")
    content: str = Field(..., description="Source content")
    category: str = Field(..., description="Content category")
    last_updated: datetime = Field(..., description="Last update timestamp")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to query")
    url: Optional[str] = Field(None, description="Source URL if available")


class KnowledgeResponse(BaseModel):
    """Knowledge base query response"""
    query: str = Field(..., description="Original query")
    sources: List[KnowledgeSource] = Field(..., description="Relevant knowledge sources")
    synthesized_answer: str = Field(..., description="Synthesized answer from sources")
    confidence: float = Field(..., ge=0, le=1, description="Answer confidence")
    search_time_ms: int = Field(..., description="Search execution time")


# ============================================================================
# WebSocket Message Models
# ============================================================================

class WebSocketMessageType(str, Enum):
    """WebSocket message types"""
    WELCOME = "welcome"
    MESSAGE = "message"
    TYPING = "typing"
    ERROR = "error"
    SYSTEM = "system"


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: WebSocketMessageType = Field(..., description="Message type")
    message: str = Field(..., description="Message content")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    session_id: Optional[str] = Field(None, description="Session identifier")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional message data")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Timestamp must be positive')
        return v


# ============================================================================
# Utility Models
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination information"""
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether next page exists")
    has_previous: bool = Field(..., description="Whether previous page exists")
    
    @model_validator(mode='after')
    def validate_total_pages(self):
        expected_pages = (self.total_items + self.page_size - 1) // self.page_size
        if self.total_pages != expected_pages:
            raise ValueError(f'Total pages {self.total_pages} does not match calculated pages {expected_pages}')
        return self


class SearchFilters(BaseModel):
    """Search filter options"""
    categories: List[str] = Field(default_factory=list, description="Category filters")
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price")
    brands: List[str] = Field(default_factory=list, description="Brand filters")
    rating_min: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    in_stock_only: bool = Field(default=True, description="Show only in-stock items")
    
    @model_validator(mode='after')
    def validate_price_range(self):
        if self.price_max is not None and self.price_min is not None:
            if self.price_max < self.price_min:
                raise ValueError('Maximum price must be greater than or equal to minimum price')
        return self