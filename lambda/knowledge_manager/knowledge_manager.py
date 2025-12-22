"""
E-Com67 Platform Knowledge Base Manager

Utility functions for managing the knowledge base documents.
This can be used by admin functions or CLI tools to manage knowledge base content.
"""

import json
import boto3
import os
import time
from typing import List, Dict, Any, Optional
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()

# Initialize AWS clients
s3_client = boto3.client('s3')

# Environment variables
KNOWLEDGE_BASE_BUCKET = os.environ.get('KNOWLEDGE_BASE_BUCKET_NAME')


class KnowledgeManagerError(Exception):
    """Custom exception for knowledge manager errors"""
    pass


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main handler for knowledge base management operations.
    
    Supports operations: upload, delete, list
    """
    try:
        operation = event.get('operation', '').lower()
        
        if operation == 'upload':
            return handle_upload(event)
        elif operation == 'delete':
            return handle_delete(event)
        elif operation == 'list':
            return handle_list(event)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid operation',
                    'supported_operations': ['upload', 'delete', 'list']
                })
            }
    
    except Exception as e:
        logger.exception(f"Error in knowledge manager: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


def handle_upload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle document upload to knowledge base"""
    try:
        filename = event.get('filename')
        content = event.get('content')
        
        if not filename or not content:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: filename and content'
                })
            }
        
        # Upload document to S3
        success = upload_knowledge_document(content, filename)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully uploaded document: {filename}',
                    'filename': filename,
                    'bucket': KNOWLEDGE_BASE_BUCKET,
                    'key': f'documents/{filename}'
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Failed to upload document: {filename}'
                })
            }
    
    except Exception as e:
        logger.exception(f"Error uploading document: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Upload failed',
                'message': str(e)
            })
        }


def handle_delete(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle document deletion from knowledge base"""
    try:
        filename = event.get('filename')
        
        if not filename:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: filename'
                })
            }
        
        # Delete document from S3
        success = delete_knowledge_document(filename)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully deleted document: {filename}',
                    'filename': filename
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Failed to delete document: {filename}'
                })
            }
    
    except Exception as e:
        logger.exception(f"Error deleting document: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Delete failed',
                'message': str(e)
            })
        }


def handle_list(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle listing documents in knowledge base"""
    try:
        documents = list_knowledge_documents()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Found {len(documents)} documents in knowledge base',
                'documents': documents,
                'bucket': KNOWLEDGE_BASE_BUCKET
            })
        }
    
    except Exception as e:
        logger.exception(f"Error listing documents: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'List failed',
                'message': str(e)
            })
        }


def upload_knowledge_document(content: str, filename: str) -> bool:
    """Upload a document to the knowledge base"""
    try:
        # Ensure filename has proper path
        key = f"documents/{filename}" if not filename.startswith('documents/') else filename
        
        # Upload to S3
        s3_client.put_object(
            Bucket=KNOWLEDGE_BASE_BUCKET,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/plain',
            Metadata={
                'uploaded_at': str(int(time.time())),
                'source': 'knowledge_manager'
            }
        )
        
        logger.info(f"Successfully uploaded document: {key}")
        return True
        
    except Exception as e:
        logger.exception(f"Error uploading document {filename}: {str(e)}")
        return False


def delete_knowledge_document(filename: str) -> bool:
    """Remove a document from the knowledge base"""
    try:
        # Ensure filename has proper path
        key = f"documents/{filename}" if not filename.startswith('documents/') else filename
        
        # Delete from S3
        s3_client.delete_object(
            Bucket=KNOWLEDGE_BASE_BUCKET,
            Key=key
        )
        
        logger.info(f"Successfully deleted document: {key}")
        return True
        
    except Exception as e:
        logger.exception(f"Error deleting document {filename}: {str(e)}")
        return False


def list_knowledge_documents() -> List[Dict[str, Any]]:
    """List all documents in the knowledge base"""
    try:
        documents = []
        
        # List objects in the documents/ prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=KNOWLEDGE_BASE_BUCKET,
            Prefix='documents/'
        )
        
        for page in pages:
            for obj in page.get('Contents', []):
                # Skip directories
                if obj['Key'].endswith('/'):
                    continue
                
                documents.append({
                    'filename': obj['Key'].replace('documents/', ''),
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                })
        
        logger.info(f"Found {len(documents)} documents in knowledge base")
        return documents
        
    except Exception as e:
        logger.exception(f"Error listing documents: {str(e)}")
        return []


def create_sample_documents() -> Dict[str, str]:
    """Create sample documents for testing the knowledge base"""
    sample_docs = {
        'product-guide.txt': """
E-Com67 Product Guide

Welcome to E-Com67! Here's everything you need to know about our products.

Electronics Category:
- Laptops: High-performance laptops for work and gaming
- Smartphones: Latest models with advanced features
- Tablets: Perfect for reading and productivity
- Headphones: Premium audio quality for music lovers

Clothing Category:
- T-Shirts: Comfortable cotton t-shirts in various colors
- Jeans: Durable denim jeans for everyday wear
- Sneakers: Stylish and comfortable footwear
- Jackets: Weather-resistant outerwear

Home & Garden:
- Furniture: Modern and classic furniture pieces
- Kitchen Appliances: Essential tools for cooking
- Garden Tools: Everything for your outdoor space
- Decor: Beautiful items to enhance your home

All products come with a 30-day return policy and free shipping on orders over $50.
        """,
        
        'shipping-policy.txt': """
E-Com67 Shipping Policy

Shipping Options:
1. Standard Shipping (5-7 business days) - FREE on orders over $50
2. Express Shipping (2-3 business days) - $9.99
3. Overnight Shipping (1 business day) - $19.99

International Shipping:
- Available to most countries
- Delivery time: 7-14 business days
- Customs fees may apply

Order Processing:
- Orders placed before 2 PM EST ship same day
- Weekend orders ship on Monday
- Holiday processing may be delayed

Tracking:
- Tracking information sent via email
- Track your order on our website
- Customer service available for shipping questions
        """,
        
        'return-policy.txt': """
E-Com67 Return Policy

30-Day Return Window:
- Items can be returned within 30 days of delivery
- Items must be in original condition
- Original packaging required
- Return shipping label provided

Return Process:
1. Log into your account
2. Go to Order History
3. Select "Return Item"
4. Print return label
5. Package and ship item

Refund Timeline:
- Refunds processed within 3-5 business days
- Original payment method will be credited
- Shipping costs are non-refundable

Exchanges:
- Size exchanges available for clothing
- Color exchanges subject to availability
- Contact customer service for assistance

Non-Returnable Items:
- Personalized items
- Perishable goods
- Digital downloads
- Items damaged by customer
        """,
        
        'customer-support.txt': """
E-Com67 Customer Support

Contact Information:
- Phone: 1-800-ECOM67 (1-800-326-6267)
- Email: support@ecom67.com
- Live Chat: Available on our website
- Hours: Monday-Friday 9 AM - 8 PM EST

Common Questions:

Order Status:
- Check your email for tracking information
- Log into your account to view order status
- Orders typically ship within 24 hours

Payment Issues:
- We accept all major credit cards
- PayPal and Apple Pay available
- Contact us for payment problems

Technical Support:
- Website issues: Clear browser cache
- Mobile app problems: Update to latest version
- Account access: Use password reset feature

Product Information:
- Detailed specifications on product pages
- Customer reviews and ratings available
- Size guides for clothing items

Warranty Information:
- Electronics: 1-year manufacturer warranty
- Appliances: 2-year extended warranty available
- Clothing: Quality guarantee for 90 days
        """
    }
    
    return sample_docs


# CLI-style functions for direct usage
def upload_sample_documents():
    """Upload sample documents to the knowledge base"""
    sample_docs = create_sample_documents()
    
    for filename, content in sample_docs.items():
        success = upload_knowledge_document(content, filename)
        if success:
            print(f"✓ Uploaded: {filename}")
        else:
            print(f"✗ Failed to upload: {filename}")


if __name__ == "__main__":
    # For local testing
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "upload-samples":
        upload_sample_documents()
    else:
        print("Usage: python knowledge_manager.py upload-samples")