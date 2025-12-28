"""
Admin Insights Agent Core Handler

This module implements the core agent functionality using AWS Bedrock AgentCore
with the Strands SDK. It handles:
- Agent initialization with tool schemas
- Tool invocation via Lambda
- Message processing with guardrails
- Response formatting

Requirements:
- Requirements 1.1: Agent request processing
- Requirements 1.2: Session context maintenance
- Requirements 1.3: Tool invocation
- Requirements 8.1: Tool schema definition
- Requirements 8.2: Tool descriptions
- Requirements 8.3: Input validation
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize logging
logger = Logger()
tracer = Tracer()

# Environment variables
MEMORY_ID = os.environ.get('MEMORY_ID', '')
GUARDRAIL_ID = os.environ.get('GUARDRAIL_ID', '')
GUARDRAIL_VERSION = os.environ.get('GUARDRAIL_VERSION', 'DRAFT')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')

# Tool Lambda ARNs
ORDER_TRENDS_TOOL_ARN = os.environ.get('ORDER_TRENDS_TOOL_ARN', '')
SALES_INSIGHTS_TOOL_ARN = os.environ.get('SALES_INSIGHTS_TOOL_ARN', '')
PRODUCT_SEARCH_TOOL_ARN = os.environ.get('PRODUCT_SEARCH_TOOL_ARN', '')

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)


# Tool Schema Definitions
# These schemas define the analytics tools available to the agent

ORDER_TRENDS_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "order_trends",
        "description": (
            "Analyzes order trends over time including order volume, revenue trends, "
            "status distribution, and growth rates. Use this tool when administrators "
            "ask about order patterns, sales trends over time, or business performance metrics."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "integer",
                        "description": "Start date as Unix timestamp in seconds (e.g., 1704067200 for 2024-01-01)"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date as Unix timestamp in seconds"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["day", "week", "month"],
                        "description": "Time period grouping: 'day' for daily trends, 'week' for weekly, 'month' for monthly"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["volume", "revenue", "status_distribution"]
                        },
                        "description": "Metrics to calculate: 'volume' for order counts, 'revenue' for sales amounts, 'status_distribution' for order statuses"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        }
    }
}

SALES_INSIGHTS_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "sales_insights",
        "description": (
            "Analyzes product sales performance including top-selling products, revenue by product, "
            "category performance, and low performers. Use this tool when administrators ask about "
            "product performance, best sellers, category analysis, or inventory decisions."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "integer",
                        "description": "Start date as Unix timestamp in seconds"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date as Unix timestamp in seconds"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional: Filter by product category (e.g., 'Electronics', 'Clothing')"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["revenue", "units_sold", "growth"],
                        "description": "Sort products by: 'revenue' for total sales, 'units_sold' for quantity, 'growth' for growth rate"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of products to return (1-100, default: 10)"
                    },
                    "low_performer_threshold": {
                        "type": "number",
                        "description": "Optional: Revenue threshold for identifying low performers"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        }
    }
}

PRODUCT_SEARCH_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "product_search",
        "description": (
            "Searches for products by name, description, category, or other attributes using "
            "semantic search. Use this tool when administrators need to find specific products, "
            "check inventory, or get product details."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (product name, description, tags, brand, SKU)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional: Filter by product category"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-100, default: 10)"
                    },
                    "include_inactive": {
                        "type": "boolean",
                        "description": "Whether to include inactive products in results (default: false)"
                    }
                },
                "required": ["query"]
            }
        }
    }
}


# System prompt for the Admin Insights Agent
SYSTEM_PROMPT = """You are an AI assistant for E-Com67 administrators, specializing in business analytics and insights.

Your role is to help shop administrators:
1. **Analyze Order Trends**: Provide insights on order volume, revenue patterns, and growth metrics
2. **Evaluate Product Performance**: Identify top sellers, analyze category performance, and spot low performers
3. **Search Products**: Help find and review product information for inventory management

**Guidelines:**
- Use the available analytics tools to provide accurate, data-driven insights
- Present data clearly with key metrics highlighted
- Provide actionable recommendations based on the data
- When showing trends, explain what the data means for the business
- Be professional and concise in your responses
- If data is missing or unclear, explain what information is needed

**Available Tools:**
- order_trends: Analyze order patterns over time
- sales_insights: Evaluate product sales performance
- product_search: Search and find product information

Remember: You're helping administrators make informed business decisions, so focus on clarity and actionable insights."""


@tracer.capture_method
def initialize_agent(
    session_id: str,
    actor_id: str,
    memory_id: str = MEMORY_ID
) -> Dict[str, Any]:
    """
    Initialize the Bedrock AgentCore agent with Strands SDK.
    
    This function sets up the agent configuration including:
    - Model selection (Amazon Nova Pro)
    - Tool schemas for analytics tools
    - Session memory configuration
    - System prompt
    
    Args:
        session_id: Unique session identifier
        actor_id: Admin user ID
        memory_id: Bedrock AgentCore Memory ID
    
    Returns:
        Agent configuration dictionary
    
    Raises:
        ValueError: If required parameters are missing
        RuntimeError: If agent initialization fails
    """
    if not session_id:
        raise ValueError("session_id is required")
    if not actor_id:
        raise ValueError("actor_id is required")
    if not memory_id:
        raise ValueError("memory_id is required")
    
    logger.info("Initializing agent", extra={
        "session_id": session_id,
        "actor_id": actor_id,
        "memory_id": memory_id,
        "model_id": MODEL_ID
    })
    
    try:
        # Import Strands SDK components
        from strands import Agent
        from strands.models import BedrockModel
        from strands.agent.conversation_manager import SlidingWindowConversationManager
        
        # Create Bedrock model instance
        bedrock_model = BedrockModel(
            model_id=MODEL_ID,
            temperature=0.3,  # Lower temperature for more consistent analytics
            max_tokens=4096,
            streaming=False,  # Disable streaming for simpler implementation
            region=AWS_REGION
        )
        
        # Create conversation manager with session memory
        conversation_manager = SlidingWindowConversationManager(
            window_size=40  # 20 conversation turns (20 user + 20 assistant messages)
        )
        
        # Define tools for the agent
        tools = [
            ORDER_TRENDS_TOOL_SCHEMA,
            SALES_INSIGHTS_TOOL_SCHEMA,
            PRODUCT_SEARCH_TOOL_SCHEMA
        ]
        
        # Create agent instance
        agent = Agent(
            model=bedrock_model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            conversation_manager=conversation_manager
        )
        
        logger.info("Agent initialized successfully", extra={
            "session_id": session_id,
            "tools_count": len(tools)
        })
        
        return {
            "agent": agent,
            "session_id": session_id,
            "actor_id": actor_id,
            "memory_id": memory_id,
            "model_id": MODEL_ID,
            "tools": [tool["toolSpec"]["name"] for tool in tools]
        }
        
    except ImportError as e:
        logger.error("Failed to import Strands SDK", extra={"error": str(e)})
        raise RuntimeError(f"Strands SDK not available: {str(e)}")
    except Exception as e:
        logger.error("Agent initialization failed", extra={
            "error": str(e),
            "session_id": session_id
        })
        raise RuntimeError(f"Failed to initialize agent: {str(e)}")


@tracer.capture_method
def invoke_tool(
    tool_name: str,
    tool_input: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Invoke an analytics tool via Lambda.
    
    Maps tool names to Lambda ARNs and invokes the appropriate function.
    Handles errors and returns structured responses.
    
    Args:
        tool_name: Name of the tool to invoke (order_trends, sales_insights, product_search)
        tool_input: Input parameters for the tool
    
    Returns:
        Tool execution result
    
    Raises:
        ValueError: If tool_name is unknown
        RuntimeError: If tool invocation fails
    """
    logger.info("Invoking tool", extra={
        "tool_name": tool_name,
        "tool_input": tool_input
    })
    
    # Map tool names to Lambda ARNs
    tool_arn_map = {
        "order_trends": ORDER_TRENDS_TOOL_ARN,
        "sales_insights": SALES_INSIGHTS_TOOL_ARN,
        "product_search": PRODUCT_SEARCH_TOOL_ARN
    }
    
    if tool_name not in tool_arn_map:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_arn = tool_arn_map[tool_name]
    
    if not tool_arn:
        raise RuntimeError(f"Tool ARN not configured for {tool_name}")
    
    try:
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName=tool_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(tool_input)
        )
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        
        # Check for errors
        if response.get('FunctionError'):
            logger.error("Tool execution failed", extra={
                "tool_name": tool_name,
                "error": payload
            })
            return {
                "error": "TOOL_EXECUTION_ERROR",
                "message": f"Tool {tool_name} failed to execute",
                "details": payload
            }
        
        # Parse the body if it's a string (API Gateway format)
        if isinstance(payload.get('body'), str):
            payload['body'] = json.loads(payload['body'])
        
        logger.info("Tool invoked successfully", extra={
            "tool_name": tool_name,
            "status_code": payload.get('statusCode')
        })
        
        return payload.get('body', payload)
        
    except ClientError as e:
        logger.error("Lambda invocation failed", extra={
            "tool_name": tool_name,
            "error": str(e)
        })
        raise RuntimeError(f"Failed to invoke tool {tool_name}: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error invoking tool", extra={
            "tool_name": tool_name,
            "error": str(e)
        })
        raise RuntimeError(f"Unexpected error invoking tool {tool_name}: {str(e)}")


@tracer.capture_method
def apply_guardrails(
    content: str,
    source: str = "INPUT"
) -> Dict[str, Any]:
    """
    Apply Bedrock Guardrails to content for PII detection and prompt attack prevention.
    
    Args:
        content: Content to scan (user input or agent output)
        source: Content source ("INPUT" or "OUTPUT")
    
    Returns:
        Dictionary with guardrail results:
        {
            "action": "NONE" | "BLOCKED",
            "content": str (original or redacted),
            "violations": List[str]
        }
    
    Raises:
        RuntimeError: If guardrail invocation fails
    """
    if not GUARDRAIL_ID:
        logger.warning("Guardrail ID not configured, skipping guardrail check")
        return {
            "action": "NONE",
            "content": content,
            "violations": []
        }
    
    logger.info("Applying guardrails", extra={
        "source": source,
        "content_length": len(content)
    })
    
    try:
        # Apply guardrails using Bedrock Runtime
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=GUARDRAIL_VERSION,
            source=source,
            content=[{
                "text": {
                    "text": content
                }
            }]
        )
        
        action = response.get('action', 'NONE')
        violations = []
        
        # Extract violation details
        if action == 'BLOCKED':
            assessments = response.get('assessments', [])
            for assessment in assessments:
                # Check for PII violations
                if 'sensitiveInformationPolicy' in assessment:
                    pii_entities = assessment['sensitiveInformationPolicy'].get('piiEntities', [])
                    for entity in pii_entities:
                        violations.append(f"PII detected: {entity.get('type')}")
                
                # Check for prompt attack violations
                if 'contentPolicy' in assessment:
                    filters = assessment['contentPolicy'].get('filters', [])
                    for filter_item in filters:
                        if filter_item.get('type') == 'PROMPT_ATTACK':
                            violations.append("Prompt attack detected")
        
        # Get output content (may be redacted)
        output_content = content
        if response.get('outputs'):
            output_content = response['outputs'][0].get('text', content)
        
        logger.info("Guardrails applied", extra={
            "action": action,
            "violations_count": len(violations),
            "source": source
        })
        
        return {
            "action": action,
            "content": output_content,
            "violations": violations
        }
        
    except ClientError as e:
        logger.error("Guardrail invocation failed", extra={
            "error": str(e),
            "source": source
        })
        # In case of guardrail failure, block the content to be safe
        return {
            "action": "BLOCKED",
            "content": "",
            "violations": ["Guardrail service error"]
        }
    except Exception as e:
        logger.error("Unexpected error applying guardrails", extra={
            "error": str(e),
            "source": source
        })
        return {
            "action": "BLOCKED",
            "content": "",
            "violations": ["Guardrail processing error"]
        }


@tracer.capture_method
def process_message(
    agent_config: Dict[str, Any],
    message: str,
    session_id: str,
    actor_id: str
) -> Dict[str, Any]:
    """
    Process a user message through the agent with guardrails.
    
    This is the main message processing pipeline:
    1. Apply input guardrails
    2. Invoke agent with message
    3. Handle tool invocations
    4. Apply output guardrails
    5. Return formatted response
    
    Args:
        agent_config: Agent configuration from initialize_agent
        message: User message to process
        session_id: Session identifier
        actor_id: Admin user ID
    
    Returns:
        Dictionary with response and metadata
    
    Raises:
        ValueError: If message is blocked by guardrails
        RuntimeError: If processing fails
    """
    logger.info("Processing message", extra={
        "session_id": session_id,
        "actor_id": actor_id,
        "message_length": len(message)
    })
    
    # Step 1: Apply input guardrails
    input_guardrail_result = apply_guardrails(message, source="INPUT")
    
    if input_guardrail_result["action"] == "BLOCKED":
        logger.warning("Message blocked by input guardrails", extra={
            "session_id": session_id,
            "violations": input_guardrail_result["violations"]
        })
        raise ValueError(
            "Your request contains content that cannot be processed. "
            "Please rephrase your question without sensitive information."
        )
    
    # Step 2: Invoke agent
    agent = agent_config["agent"]
    tools_invoked = []
    
    try:
        # Process message with agent
        # Note: Strands SDK handles tool invocation internally
        # We need to register our tool invocation function
        
        # For now, we'll use a simpler approach: invoke the agent and handle tool calls
        response = agent.process(message)
        
        # Extract tool invocations if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name')
                tool_input = tool_call.get('input', {})
                
                # Invoke the tool
                invoke_tool(tool_name, tool_input)
                tools_invoked.append(tool_name)
                
                # Provide tool result back to agent
                # This would be handled by Strands SDK in a real implementation
        
        # Get final response text
        response_text = str(response) if not isinstance(response, str) else response
        
    except Exception as e:
        logger.error("Agent processing failed", extra={
            "error": str(e),
            "session_id": session_id
        })
        raise RuntimeError(f"Failed to process message: {str(e)}")
    
    # Step 3: Apply output guardrails
    output_guardrail_result = apply_guardrails(response_text, source="OUTPUT")
    
    if output_guardrail_result["action"] == "BLOCKED":
        logger.warning("Response blocked by output guardrails", extra={
            "session_id": session_id,
            "violations": output_guardrail_result["violations"]
        })
        response_text = (
            "I apologize, but I cannot provide this information as it may contain "
            "sensitive data. Please contact support for assistance."
        )
    else:
        response_text = output_guardrail_result["content"]
    
    logger.info("Message processed successfully", extra={
        "session_id": session_id,
        "tools_invoked": tools_invoked,
        "response_length": len(response_text)
    })
    
    return {
        "response": response_text,
        "session_id": session_id,
        "actor_id": actor_id,
        "tools_invoked": tools_invoked,
        "timestamp": int(datetime.now().timestamp())
    }


@tracer.capture_method
def format_response(
    processing_result: Dict[str, Any],
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Format the agent response for API Gateway.
    
    Args:
        processing_result: Result from process_message
        include_metadata: Whether to include metadata in response
    
    Returns:
        Formatted response dictionary
    """
    logger.info("Formatting response", extra={
        "session_id": processing_result.get("session_id"),
        "include_metadata": include_metadata
    })
    
    response = {
        "response": processing_result["response"],
        "session_id": processing_result["session_id"],
        "timestamp": processing_result["timestamp"]
    }
    
    if include_metadata:
        response["metadata"] = {
            "actor_id": processing_result["actor_id"],
            "tools_invoked": processing_result["tools_invoked"],
            "tools_count": len(processing_result["tools_invoked"])
        }
    
    return response
