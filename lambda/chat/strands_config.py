"""
Strands AI Agent Configuration Module

This module provides configuration and initialization for the Strands SDK-powered
AI agent that replaces the existing Bedrock implementation in the E-Com67 platform.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# Initialize logger
logger = logging.getLogger(__name__)


class DeploymentStage(Enum):
    """Deployment stages for environment-based configuration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class BedrockModelConfig:
    """Configuration for Amazon Bedrock model integration"""
    model_id: str
    temperature: float
    max_tokens: int
    streaming: bool
    region: str


@dataclass
class StrandsAgentConfig:
    """Configuration class for Strands AI Agent"""
    
    # Model configuration
    bedrock_config: BedrockModelConfig
    
    # Agent parameters
    system_prompt: str
    conversation_memory_limit: int
    tool_timeout_seconds: int
    
    # Environment settings
    deployment_stage: DeploymentStage
    debug_mode: bool
    
    # E-Com67 specific settings
    platform_name: str
    platform_version: str
    
    @classmethod
    def from_environment(cls) -> 'StrandsAgentConfig':
        """Create configuration from environment variables"""
        
        # Get deployment stage
        stage_str = os.environ.get('DEPLOYMENT_STAGE', 'development').lower()
        try:
            deployment_stage = DeploymentStage(stage_str)
        except ValueError:
            logger.warning(f"Invalid deployment stage '{stage_str}', defaulting to development")
            deployment_stage = DeploymentStage.DEVELOPMENT
        
        # Configure Bedrock model based on stage
        bedrock_config = BedrockModelConfig(
            model_id=os.environ.get('BEDROCK_MODEL_ID', 'amazon.titan-text-express-v1'),
            temperature=float(os.environ.get('BEDROCK_TEMPERATURE', '0.7')),
            max_tokens=int(os.environ.get('BEDROCK_MAX_TOKENS', '4096')),
            streaming=os.environ.get('BEDROCK_STREAMING', 'false').lower() == 'true',
            region=os.environ.get('AWS_REGION', 'ap-southeast-1')
        )
        
        # Configure agent parameters based on stage
        if deployment_stage == DeploymentStage.PRODUCTION:
            conversation_memory_limit = 20
            tool_timeout_seconds = 25
            debug_mode = False
        elif deployment_stage == DeploymentStage.STAGING:
            conversation_memory_limit = 15
            tool_timeout_seconds = 20
            debug_mode = True
        else:  # DEVELOPMENT
            conversation_memory_limit = 10
            tool_timeout_seconds = 15
            debug_mode = True
        
        return cls(
            bedrock_config=bedrock_config,
            system_prompt=cls._get_system_prompt(),
            conversation_memory_limit=conversation_memory_limit,
            tool_timeout_seconds=tool_timeout_seconds,
            deployment_stage=deployment_stage,
            debug_mode=debug_mode,
            platform_name="E-Com67",
            platform_version=os.environ.get('PLATFORM_VERSION', '1.0.0')
        )
    
    @staticmethod
    def _get_system_prompt() -> str:
        """Get the system prompt for E-Com67 context"""
        return """You are an AI assistant for E-Com67, a modern e-commerce platform. 
You help customers with:

1. **Product Discovery**: Search for products, provide detailed information, and make personalized recommendations
2. **Shopping Cart Management**: Add, remove, or modify items in the customer's cart
3. **Order Tracking**: Provide information about order status, shipping, and delivery
4. **Customer Support**: Answer questions about policies, shipping, returns, and general platform usage

**Guidelines:**
- Always use the available tools to provide accurate, up-to-date information
- Be helpful, friendly, and professional in all interactions
- If you don't have specific information, be honest and suggest alternative ways to get help
- Format responses clearly and provide actionable suggestions when appropriate
- Maintain conversation context to provide personalized assistance
- Prioritize customer satisfaction while following platform policies

**Available Tools:**
- Product search and recommendation tools
- Cart management tools  
- Order query and tracking tools
- Knowledge base search for policies and information

Remember: You represent the E-Com67 brand, so maintain a professional yet approachable tone that reflects our commitment to excellent customer service."""


class StrandsAgentManager:
    """Manager class for Strands agent initialization and lifecycle"""
    
    def __init__(self, config: Optional[StrandsAgentConfig] = None):
        """Initialize the agent manager with configuration"""
        self.config = config or StrandsAgentConfig.from_environment()
        self._agent = None
        self._tools_cache = {}
        
        logger.info(f"Initialized StrandsAgentManager for {self.config.deployment_stage.value} environment")
    
    def get_agent(self, user_context: Optional[Dict[str, Any]] = None):
        """
        Get or create a Strands agent instance.

        Args:
            user_context: Optional user-specific context for personalization

        Returns:
            Configured Strands agent instance
        """
        try:
            # Import Strands SDK components
            from strands import Agent
            from strands.models import BedrockModel
            from strands.agent.conversation_manager import SlidingWindowConversationManager

            # Create Bedrock model instance
            bedrock_model = BedrockModel(
                model_id=self.config.bedrock_config.model_id,
                temperature=self.config.bedrock_config.temperature,
                max_tokens=self.config.bedrock_config.max_tokens,
                streaming=self.config.bedrock_config.streaming,
                region=self.config.bedrock_config.region
            )

            # Get custom tools for the agent
            tools = self._get_custom_tools(user_context)

            # Create conversation manager with sliding window
            conversation_manager = SlidingWindowConversationManager(
                window_size=self.config.conversation_memory_limit * 2  # Each exchange has 2 messages (user + assistant)
            )

            # Create agent instance with correct Strands SDK API
            agent = Agent(
                model=bedrock_model,
                tools=tools,
                system_prompt=self._get_contextualized_system_prompt(user_context),
                conversation_manager=conversation_manager
            )

            logger.info(f"Created Strands agent with {len(tools)} tools")

            return agent

        except ImportError as e:
            logger.error(f"Strands SDK not available: {str(e)}")
            raise RuntimeError("Strands SDK is not properly installed or configured")
        except Exception as e:
            logger.exception(f"Error creating Strands agent: {str(e)}")
            raise RuntimeError(f"Failed to initialize Strands agent: {str(e)}")
    
    def _get_custom_tools(self, user_context: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Get custom tools for the Strands agent.
        
        Args:
            user_context: User-specific context for tool initialization
            
        Returns:
            List of configured tools
        """
        tools = []
        
        try:
            # Import custom tool functions (decorated with @tool)
            from tools.product_search_tool import product_search, get_product_details, get_product_recommendations
            from tools.cart_management_tool import add_to_cart, get_cart_contents, update_cart_item, remove_from_cart, clear_cart
            from tools.order_query_tool import get_order_history, get_order_details, track_order, search_orders
            from tools.knowledge_base_tool import search_knowledge_base, get_platform_info, get_help_topics
            
            # Add all tool functions to the tools list
            tools.extend([
                # Product search tools
                product_search,
                get_product_details,
                get_product_recommendations,
                
                # Cart management tools
                add_to_cart,
                get_cart_contents,
                update_cart_item,
                remove_from_cart,
                clear_cart,
                
                # Order query tools
                get_order_history,
                get_order_details,
                track_order,
                search_orders,
                
                # Knowledge base tools
                search_knowledge_base,
                get_platform_info,
                get_help_topics
            ])
            
            logger.debug(f"Loaded {len(tools)} custom tools for agent")
            
        except ImportError as e:
            logger.warning(f"Some custom tools not available: {str(e)}")
            # In development, we can continue without all tools
            if self.config.deployment_stage != DeploymentStage.DEVELOPMENT:
                raise RuntimeError(f"Required tools not available: {str(e)}")
        
        return tools
    
    def _get_contextualized_system_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get system prompt with user-specific context.
        
        Args:
            user_context: User-specific context for personalization
            
        Returns:
            Contextualized system prompt
        """
        base_prompt = self.config.system_prompt
        
        if user_context:
            user_id = user_context.get('user_id', 'anonymous')
            session_id = user_context.get('session_id', 'new')
            
            context_addition = f"""

**Current Session Context:**
- User ID: {user_id}
- Session ID: {session_id}
- Platform: {self.config.platform_name} v{self.config.platform_version}
- Environment: {self.config.deployment_stage.value}

Personalize your responses based on this user's context when appropriate."""
            
            return base_prompt + context_addition
        
        return base_prompt
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration and return status.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'config_summary': {
                'deployment_stage': self.config.deployment_stage.value,
                'model_id': self.config.bedrock_config.model_id,
                'debug_mode': self.config.debug_mode,
                'memory_limit': self.config.conversation_memory_limit
            }
        }
        
        # Validate Bedrock configuration
        if not self.config.bedrock_config.model_id:
            validation_results['errors'].append("Bedrock model ID is not configured")
            validation_results['valid'] = False
        
        if self.config.bedrock_config.temperature < 0 or self.config.bedrock_config.temperature > 1:
            validation_results['warnings'].append("Bedrock temperature should be between 0 and 1")
        
        if self.config.bedrock_config.max_tokens < 100:
            validation_results['warnings'].append("Max tokens is very low, may truncate responses")
        
        # Validate environment settings
        if self.config.tool_timeout_seconds < 5:
            validation_results['warnings'].append("Tool timeout is very low, may cause failures")
        
        # Check for required environment variables
        required_env_vars = [
            'CHAT_HISTORY_TABLE_NAME',
            'PRODUCTS_TABLE_NAME',
            'AWS_REGION'
        ]
        
        for env_var in required_env_vars:
            if not os.environ.get(env_var):
                validation_results['errors'].append(f"Required environment variable {env_var} is not set")
                validation_results['valid'] = False
        
        return validation_results


def get_default_agent_manager() -> StrandsAgentManager:
    """Get a default configured agent manager instance"""
    return StrandsAgentManager()


def test_strands_sdk_import() -> Dict[str, Any]:
    """
    Test Strands SDK import and basic functionality.
    
    Returns:
        Dictionary with test results
    """
    test_results = {
        'sdk_available': False,
        'import_errors': [],
        'version_info': {},
        'basic_functionality': False
    }
    
    try:
        # Test basic imports
        from strands import Agent
        from strands.models import BedrockModel
        test_results['sdk_available'] = True
        
        # Try to get version information
        try:
            import strands
            if hasattr(strands, '__version__'):
                test_results['version_info']['strands'] = strands.__version__
        except:
            pass
        
        # Test basic model creation (without actual initialization)
        try:
            model_config = BedrockModel(
                model_id="amazon.titan-text-express-v1",
                temperature=0.7,
                streaming=False
            )
            test_results['basic_functionality'] = True
        except Exception as e:
            test_results['import_errors'].append(f"Model creation failed: {str(e)}")
        
    except ImportError as e:
        test_results['import_errors'].append(f"Strands SDK import failed: {str(e)}")
    except Exception as e:
        test_results['import_errors'].append(f"Unexpected error: {str(e)}")
    
    return test_results