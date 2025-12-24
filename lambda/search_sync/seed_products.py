#!/usr/bin/env python3
"""
Seed script to add 10 dummy test products to the DynamoDB products table.

Usage:
    python seed_products.py

This script creates sample products across different categories for testing
the search sync functionality and OpenSearch indexing.
"""

import boto3
import uuid
import time
from decimal import Decimal

# Configuration
TABLE_NAME = "e-com67-products"
REGION = "ap-southeast-1"

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# Sample products data
PRODUCTS = [
    {
        "name": "MacBook Pro 16-inch",
        "description": "Powerful laptop with M3 Pro chip, 18GB RAM, and 512GB SSD. Perfect for developers and creative professionals.",
        "category": "Electronics",
        "price": 2499.99,
        "stock": 25,
        "tags": ["laptop", "apple", "macbook", "computer"],
        "imageUrl": "https://example.com/images/macbook-pro.jpg"
    },
    {
        "name": "Sony WH-1000XM5 Headphones",
        "description": "Industry-leading noise canceling wireless headphones with exceptional sound quality and 30-hour battery life.",
        "category": "Electronics",
        "price": 349.99,
        "stock": 50,
        "tags": ["headphones", "sony", "wireless", "noise-canceling"],
        "imageUrl": "https://example.com/images/sony-headphones.jpg"
    },
    {
        "name": "Ergonomic Office Chair",
        "description": "Premium mesh office chair with lumbar support, adjustable armrests, and breathable material for all-day comfort.",
        "category": "Furniture",
        "price": 459.00,
        "stock": 15,
        "tags": ["chair", "office", "ergonomic", "furniture"],
        "imageUrl": "https://example.com/images/office-chair.jpg"
    },
    {
        "name": "Samsung 4K Smart TV 55-inch",
        "description": "Crystal clear 4K UHD display with smart TV features, HDR support, and built-in streaming apps.",
        "category": "Electronics",
        "price": 699.99,
        "stock": 30,
        "tags": ["tv", "samsung", "4k", "smart-tv"],
        "imageUrl": "https://example.com/images/samsung-tv.jpg"
    },
    {
        "name": "Nike Air Max 270",
        "description": "Comfortable running shoes with Max Air unit for cushioning. Lightweight and stylish design.",
        "category": "Footwear",
        "price": 150.00,
        "stock": 100,
        "tags": ["shoes", "nike", "running", "sports"],
        "imageUrl": "https://example.com/images/nike-airmax.jpg"
    },
    {
        "name": "Instant Pot Duo 7-in-1",
        "description": "Multi-functional pressure cooker that works as slow cooker, rice cooker, steamer, and more. 6-quart capacity.",
        "category": "Kitchen",
        "price": 89.99,
        "stock": 45,
        "tags": ["kitchen", "cooking", "pressure-cooker", "instant-pot"],
        "imageUrl": "https://example.com/images/instant-pot.jpg"
    },
    {
        "name": "Levi's 501 Original Jeans",
        "description": "Classic straight fit jeans made from premium denim. Timeless style that never goes out of fashion.",
        "category": "Clothing",
        "price": 79.50,
        "stock": 200,
        "tags": ["jeans", "levis", "denim", "clothing"],
        "imageUrl": "https://example.com/images/levis-jeans.jpg"
    },
    {
        "name": "Kindle Paperwhite",
        "description": "Waterproof e-reader with 6.8-inch display, adjustable warm light, and 8GB storage. Weeks of battery life.",
        "category": "Electronics",
        "price": 139.99,
        "stock": 60,
        "tags": ["kindle", "ebook", "reader", "amazon"],
        "imageUrl": "https://example.com/images/kindle.jpg"
    },
    {
        "name": "Yoga Mat Premium",
        "description": "Extra thick 6mm yoga mat with non-slip surface. Eco-friendly TPE material, includes carrying strap.",
        "category": "Sports",
        "price": 35.99,
        "stock": 80,
        "tags": ["yoga", "fitness", "exercise", "mat"],
        "imageUrl": "https://example.com/images/yoga-mat.jpg"
    },
    {
        "name": "Nespresso Vertuo Coffee Machine",
        "description": "Single-serve coffee maker with centrifusion technology. Makes espresso, double espresso, and coffee.",
        "category": "Kitchen",
        "price": 199.00,
        "stock": 35,
        "tags": ["coffee", "nespresso", "kitchen", "espresso"],
        "imageUrl": "https://example.com/images/nespresso.jpg"
    }
]


def create_product(product_data: dict) -> dict:
    """Create a product item with all required fields."""
    current_time = int(time.time())

    return {
        "productId": str(uuid.uuid4()),
        "name": product_data["name"],
        "description": product_data["description"],
        "category": product_data["category"],
        "price": Decimal(str(product_data["price"])),  # DynamoDB requires Decimal
        "stock": product_data["stock"],
        "tags": product_data["tags"],
        "imageUrl": product_data.get("imageUrl", ""),
        "isActive": True,
        "createdAt": current_time,
        "updatedAt": current_time
    }


def seed_products():
    """Insert all dummy products into DynamoDB."""
    print(f"Seeding {len(PRODUCTS)} products into {TABLE_NAME}...")
    print("-" * 50)

    success_count = 0

    for product_data in PRODUCTS:
        product = create_product(product_data)

        try:
            table.put_item(Item=product)
            print(f"✓ Created: {product['name']} (ID: {product['productId']})")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to create {product_data['name']}: {str(e)}")

    print("-" * 50)
    print(f"Successfully created {success_count}/{len(PRODUCTS)} products")

    if success_count > 0:
        print("\nProducts should now be synced to OpenSearch via DynamoDB Streams.")


if __name__ == "__main__":
    seed_products()
