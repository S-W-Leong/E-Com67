#!/usr/bin/env python3
"""
Script to populate the products DynamoDB table with 10 dummy products.

Usage:
    python populate_products.py [--region ap-southeast-1] [--table-name e-com67-products]
"""

import boto3
import uuid
from decimal import Decimal
import argparse
from datetime import datetime

# Dummy products data
DUMMY_PRODUCTS = [
    {
        "name": "Wireless Bluetooth Headphones",
        "description": "High-quality wireless headphones with noise cancellation and 30-hour battery life",
        "price": 129.99,
        "category": "Electronics",
        "stock": 50,
        "image_url": "https://example.com/images/headphones.jpg"
    },
    {
        "name": "USB-C Charging Cable",
        "description": "Durable 2-meter USB-C cable with fast charging support up to 100W",
        "price": 14.99,
        "category": "Accessories",
        "stock": 200,
        "image_url": "https://example.com/images/usb-c-cable.jpg"
    },
    {
        "name": "Portable Phone Stand",
        "description": "Adjustable metal phone stand compatible with all phone sizes",
        "price": 9.99,
        "category": "Accessories",
        "stock": 150,
        "image_url": "https://example.com/images/phone-stand.jpg"
    },
    {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with precision tracking and 12-month battery",
        "price": 24.99,
        "category": "Electronics",
        "stock": 75,
        "image_url": "https://example.com/images/wireless-mouse.jpg"
    },
    {
        "name": "Mechanical Keyboard RGB",
        "description": "Backlit mechanical keyboard with 104 keys and customizable RGB lighting",
        "price": 89.99,
        "category": "Electronics",
        "stock": 35,
        "image_url": "https://example.com/images/rgb-keyboard.jpg"
    },
    {
        "name": "Screen Protector (3-pack)",
        "description": "Tempered glass screen protectors for 6.1-inch smartphones",
        "price": 7.99,
        "category": "Accessories",
        "stock": 300,
        "image_url": "https://example.com/images/screen-protector.jpg"
    },
    {
        "name": "Laptop Cooling Pad",
        "description": "Dual-fan cooling pad with USB power supply for optimal laptop performance",
        "price": 34.99,
        "category": "Accessories",
        "stock": 60,
        "image_url": "https://example.com/images/cooling-pad.jpg"
    },
    {
        "name": "4K USB Webcam",
        "description": "Professional 4K webcam with auto-focus and built-in microphone",
        "price": 79.99,
        "category": "Electronics",
        "stock": 40,
        "image_url": "https://example.com/images/webcam-4k.jpg"
    },
    {
        "name": "Portable SSD 1TB",
        "description": "Fast portable SSD with 1TB storage and USB 3.1 interface",
        "price": 99.99,
        "category": "Storage",
        "stock": 45,
        "image_url": "https://example.com/images/portable-ssd.jpg"
    },
    {
        "name": "Desk Lamp LED",
        "description": "Energy-efficient LED desk lamp with adjustable brightness and color temperature",
        "price": 39.99,
        "category": "Accessories",
        "stock": 80,
        "image_url": "https://example.com/images/desk-lamp.jpg"
    }
]


def populate_products(table_name: str, region: str) -> None:
    """
    Populate the products DynamoDB table with dummy products.
    
    Args:
        table_name: Name of the DynamoDB products table
        region: AWS region
    """
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    print(f"Connecting to DynamoDB table: {table_name} in region: {region}")
    
    # Insert products
    successful = 0
    failed = 0
    
    for product_data in DUMMY_PRODUCTS:
        try:
            product_id = str(uuid.uuid4())
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            
            item = {
                "productId": product_id,
                "name": product_data["name"],
                "description": product_data["description"],
                "price": Decimal(str(product_data["price"])),
                "category": product_data["category"],
                "stock": product_data["stock"],
                "image_url": product_data["image_url"],
                "created_at": timestamp,
                "updated_at": timestamp
            }
            
            table.put_item(Item=item)
            print(f"✓ Created product: {product_data['name']} (ID: {product_id})")
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed to create product {product_data['name']}: {str(e)}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Population complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="Populate the products DynamoDB table with dummy products"
    )
    parser.add_argument(
        "--region",
        default="ap-southeast-1",
        help="AWS region (default: ap-southeast-1)"
    )
    parser.add_argument(
        "--table-name",
        default="e-com67-products",
        help="DynamoDB table name (default: e-com67-products)"
    )
    
    args = parser.parse_args()
    
    populate_products(args.table_name, args.region)


if __name__ == "__main__":
    main()
