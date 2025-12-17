"""
Custom exceptions for E-Com67 platform
"""


class ValidationError(Exception):
    """Raised when data validation fails"""
    pass


class BusinessLogicError(Exception):
    """Raised when business logic constraints are violated"""
    pass