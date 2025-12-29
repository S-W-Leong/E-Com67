#!/usr/bin/env python3
"""
Admin Insights Agent Memory Initialization Script

Creates a basic AgentCore Memory resource for the Admin Insights Agent.
This memory provides short-term, session-based conversation storage without
long-term extraction strategies.

Usage:
    python scripts/create_admin_insights_memory.py [--region REGION]

The script will:
1. Create a basic AgentCore Memory resource
2. Wait for the memory to become active
3. Output the memory ID for use in Lambda environment variables
"""

import boto3
import argparse
import sys
import time
from datetime import datetime


def create_memory(region: str = "ap-southeast-1") -> dict:
    """
    Create a basic AgentCore Memory resource for short-term event storage.
    
    Args:
        region: AWS region for the memory resource
        
    Returns:
        dict: Memory resource details including memory ID
    """
    print(f"Creating Admin Insights Agent Memory in region: {region}")
    
    # Initialize boto3 client for Bedrock AgentCore Control
    control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    try:
        # Create basic memory with short-term storage only
        # No long-term strategies are configured - just raw event storage
        memory_response = control_client.create_memory(
            name="AdminInsightsAgentMemory",
            description="Short-term conversation memory for Admin Insights Agent. "
                       "Stores session-based conversation history for contextual interactions.",
            eventExpiryDuration=7  # Events expire after 7 days
        )
        
        memory_id = memory_response['memory']['id']
        print(f"✓ Memory created successfully!")
        print(f"  Memory ID: {memory_id}")
        print(f"  Name: {memory_response['memory']['name']}")
        print(f"  Status: {memory_response['memory']['status']}")
        
        # Wait for memory to become active
        print("\nWaiting for memory to become ACTIVE...")
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = control_client.get_memory(memoryId=memory_id)
                status = status_response['memory']['status']
                
                if status == 'ACTIVE':
                    print(f"✓ Memory is now ACTIVE")
                    break
                elif status in ['FAILED', 'DELETING', 'DELETED']:
                    print(f"✗ Memory creation failed with status: {status}")
                    sys.exit(1)
                else:
                    print(f"  Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                    attempt += 1
                    
            except Exception as e:
                print(f"  Error checking status: {str(e)}")
                time.sleep(2)
                attempt += 1
        
        if attempt >= max_attempts:
            print(f"✗ Timeout waiting for memory to become active")
            sys.exit(1)
        
        return memory_response['memory']
        
    except Exception as e:
        print(f"✗ Error creating memory: {str(e)}")
        sys.exit(1)


def get_existing_memory(region: str = "ap-southeast-1") -> dict:
    """
    Check if a memory with the same name already exists.
    
    Args:
        region: AWS region to check
        
    Returns:
        dict: Existing memory details if found, None otherwise
    """
    control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    try:
        # List all memories
        response = control_client.list_memories()
        
        # Look for existing memory with the same name
        for memory_summary in response.get('memories', []):
            if memory_summary.get('name') == 'AdminInsightsAgentMemory':
                # Get full memory details
                memory_response = control_client.get_memory(
                    memoryId=memory_summary['id']
                )
                return memory_response['memory']
                
    except Exception as e:
        print(f"Warning: Error checking for existing memory: {str(e)}")
        
    return None


def main():
    """Main script function"""
    parser = argparse.ArgumentParser(
        description='Create AgentCore Memory for Admin Insights Agent'
    )
    parser.add_argument(
        '--region',
        default='ap-southeast-1',
        help='AWS region for the memory resource (default: ap-southeast-1)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force creation even if memory already exists'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Admin Insights Agent Memory Initialization")
    print("=" * 70)
    print()
    
    # Check for existing memory
    if not args.force:
        print("Checking for existing memory...")
        existing_memory = get_existing_memory(args.region)
        
        if existing_memory:
            print(f"✓ Memory already exists!")
            print(f"  Memory ID: {existing_memory['id']}")
            print(f"  Name: {existing_memory['name']}")
            print(f"  Status: {existing_memory['status']}")
            print(f"  Created: {existing_memory.get('creationDateTime', 'N/A')}")
            print()
            print("Use this Memory ID in your Lambda environment variables:")
            print(f"  MEMORY_ID={existing_memory['id']}")
            print()
            print("To create a new memory, use the --force flag")
            return
        else:
            print("No existing memory found. Creating new memory...")
            print()
    
    # Create new memory
    memory = create_memory(args.region)
    
    print()
    print("=" * 70)
    print("Memory Creation Complete!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Add the following environment variable to your Lambda function:")
    print(f"   MEMORY_ID={memory['id']}")
    print()
    print("2. Update your CDK stack (stacks/admin_insights_stack.py):")
    print("   - Add MEMORY_ID to the agent Lambda environment variables")
    print()
    print("3. Deploy your CDK stack:")
    print("   cdk deploy AdminInsightsStack")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)
