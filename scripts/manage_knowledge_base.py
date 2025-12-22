#!/usr/bin/env python3
"""
E-Com67 Knowledge Base Management CLI

Simple CLI tool for managing the knowledge base documents.
"""

import json
import boto3
import argparse
import sys
import os
from typing import Dict, Any

# Add lambda directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'knowledge_manager'))

from knowledge_manager import create_sample_documents


def get_lambda_client():
    """Get AWS Lambda client"""
    return boto3.client('lambda')


def get_s3_client():
    """Get AWS S3 client"""
    return boto3.client('s3')


def invoke_knowledge_manager(operation: str, **kwargs) -> Dict[str, Any]:
    """Invoke the knowledge manager Lambda function"""
    lambda_client = get_lambda_client()
    
    payload = {
        'operation': operation,
        **kwargs
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='e-com67-knowledge-manager',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        return result
    
    except Exception as e:
        print(f"Error invoking Lambda function: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


def upload_document(filename: str, content: str = None):
    """Upload a document to the knowledge base"""
    if content is None:
        # Read from file
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            # Use just the filename without path
            upload_filename = os.path.basename(filename)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found")
            return False
        except Exception as e:
            print(f"Error reading file '{filename}': {str(e)}")
            return False
    else:
        upload_filename = filename
    
    print(f"Uploading document: {upload_filename}")
    
    result = invoke_knowledge_manager('upload', filename=upload_filename, content=content)
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"✓ Successfully uploaded: {body['filename']}")
        return True
    else:
        body = json.loads(result['body'])
        print(f"✗ Upload failed: {body.get('error', 'Unknown error')}")
        return False


def delete_document(filename: str):
    """Delete a document from the knowledge base"""
    print(f"Deleting document: {filename}")
    
    result = invoke_knowledge_manager('delete', filename=filename)
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"✓ Successfully deleted: {body['filename']}")
        return True
    else:
        body = json.loads(result['body'])
        print(f"✗ Delete failed: {body.get('error', 'Unknown error')}")
        return False


def list_documents():
    """List all documents in the knowledge base"""
    print("Listing knowledge base documents...")
    
    result = invoke_knowledge_manager('list')
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        documents = body['documents']
        
        if documents:
            print(f"\nFound {len(documents)} documents:")
            print("-" * 80)
            print(f"{'Filename':<30} {'Size':<10} {'Last Modified':<20}")
            print("-" * 80)
            
            for doc in documents:
                size_kb = doc['size'] / 1024
                print(f"{doc['filename']:<30} {size_kb:>7.1f} KB {doc['last_modified'][:19]}")
        else:
            print("No documents found in knowledge base")
        
        return True
    else:
        body = json.loads(result['body'])
        print(f"✗ List failed: {body.get('error', 'Unknown error')}")
        return False


def upload_sample_documents():
    """Upload sample documents to the knowledge base"""
    print("Creating and uploading sample documents...")
    
    sample_docs = create_sample_documents()
    
    success_count = 0
    for filename, content in sample_docs.items():
        if upload_document(filename, content):
            success_count += 1
    
    print(f"\nUploaded {success_count}/{len(sample_docs)} sample documents")
    return success_count == len(sample_docs)


def upload_directory(directory_path: str):
    """Upload all text files from a directory"""
    if not os.path.isdir(directory_path):
        print(f"Error: Directory '{directory_path}' not found")
        return False
    
    text_extensions = {'.txt', '.md', '.markdown', '.rst', '.json', '.csv', '.html', '.htm', '.xml', '.yaml', '.yml'}
    
    files_to_upload = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in text_extensions):
                files_to_upload.append(os.path.join(root, file))
    
    if not files_to_upload:
        print(f"No text files found in directory: {directory_path}")
        return False
    
    print(f"Found {len(files_to_upload)} text files to upload")
    
    success_count = 0
    for file_path in files_to_upload:
        if upload_document(file_path):
            success_count += 1
    
    print(f"\nUploaded {success_count}/{len(files_to_upload)} files")
    return success_count == len(files_to_upload)


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='E-Com67 Knowledge Base Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a document')
    upload_parser.add_argument('filename', help='File to upload')
    
    # Upload directory command
    upload_dir_parser = subparsers.add_parser('upload-dir', help='Upload all text files from a directory')
    upload_dir_parser.add_argument('directory', help='Directory containing files to upload')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a document')
    delete_parser.add_argument('filename', help='Filename to delete')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all documents')
    
    # Upload samples command
    samples_parser = subparsers.add_parser('upload-samples', help='Upload sample documents')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'upload':
            upload_document(args.filename)
        elif args.command == 'upload-dir':
            upload_directory(args.directory)
        elif args.command == 'delete':
            delete_document(args.filename)
        elif args.command == 'list':
            list_documents()
        elif args.command == 'upload-samples':
            upload_sample_documents()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()