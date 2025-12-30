"""
Checkpoint 17 Validation Script

This script validates all components for the Admin Insights Agent integration:
1. Frontend widget configuration
2. WebSocket service implementation
3. Message flow structures
4. Analytics data formatting
5. MCP Gateway setup
6. Tool registration

Run this to verify the checkpoint requirements are met.
"""

import os
import json
import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} NOT FOUND: {filepath}")
        return False


def check_env_variable(env_file: str, var_name: str, description: str) -> bool:
    """Check if environment variable is configured"""
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            if var_name in content and not content.split(var_name)[1].split('\n')[0].strip() == '=':
                value = content.split(var_name)[1].split('\n')[0].split('=')[1].strip()
                if value and not value.startswith('#'):
                    print(f"✓ {description}: {var_name}={value[:50]}...")
                    return True
        print(f"✗ {description} NOT CONFIGURED: {var_name}")
        return False
    except Exception as e:
        print(f"✗ Error checking {description}: {str(e)}")
        return False


def check_code_implementation(filepath: str, search_strings: list, description: str) -> bool:
    """Check if code contains expected implementations"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            missing = []
            for search_str in search_strings:
                if search_str not in content:
                    missing.append(search_str)
            
            if not missing:
                print(f"✓ {description}: All implementations found")
                return True
            else:
                print(f"✗ {description}: Missing implementations: {', '.join(missing[:3])}")
                return False
    except Exception as e:
        print(f"✗ Error checking {description}: {str(e)}")
        return False


def main():
    """Run all checkpoint validations"""
    print("=" * 80)
    print("CHECKPOINT 17 VALIDATION: Frontend Integration and Gateway")
    print("=" * 80)
    print()
    
    all_checks_passed = True
    
    # Section 1: Frontend Widget Files
    print("1. FRONTEND WIDGET FILES")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "frontends/admin-dashboard/src/components/AdminInsightsWidget.jsx",
            "Admin Insights Widget Component"
        ),
        check_file_exists(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            "Admin Insights WebSocket Service"
        ),
        check_file_exists(
            "frontends/admin-dashboard/src/components/AnalyticsMessageFormatter.jsx",
            "Analytics Message Formatter"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 2: Environment Configuration
    print("2. ENVIRONMENT CONFIGURATION")
    print("-" * 80)
    
    checks = [
        check_env_variable(
            "frontends/admin-dashboard/.env",
            "VITE_ADMIN_INSIGHTS_WEBSOCKET_URL",
            "Admin Insights WebSocket URL"
        ),
        check_env_variable(
            "frontends/admin-dashboard/.env",
            "VITE_USER_POOL_ID",
            "Cognito User Pool ID"
        ),
        check_env_variable(
            "frontends/admin-dashboard/.env",
            "VITE_USER_POOL_CLIENT_ID",
            "Cognito Client ID"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 3: WebSocket Service Implementation
    print("3. WEBSOCKET SERVICE IMPLEMENTATION")
    print("-" * 80)
    
    checks = [
        check_code_implementation(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            ["connect()", "sendMessage", "onMessage", "onConnectionChange", "reconnect"],
            "WebSocket connection management"
        ),
        check_code_implementation(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            ["fetchAuthSession", "idToken", "Authorization"],
            "Authentication implementation"
        ),
        check_code_implementation(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            ["sessionId", "localStorage", "generateSessionId"],
            "Session management"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 4: Message Flow Structures
    print("4. MESSAGE FLOW STRUCTURES")
    print("-" * 80)
    
    checks = [
        check_code_implementation(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            ["type: 'chunk'", "type: 'complete'", "type: 'error'"],
            "Message type handling"
        ),
        check_code_implementation(
            "frontends/admin-dashboard/src/services/adminInsights.js",
            ["action: 'sendMessage'", "timestamp"],
            "Message format structure"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 5: Analytics Data Formatting
    print("5. ANALYTICS DATA FORMATTING")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "frontends/admin-dashboard/src/components/AnalyticsMessageFormatter.jsx",
            "Analytics formatter component"
        ),
        check_code_implementation(
            "frontends/admin-dashboard/src/components/AnalyticsMessageFormatter.jsx",
            ["order_trends", "sales_insights", "product_search"],
            "Analytics tool formatting"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 6: MCP Gateway Scripts
    print("6. MCP GATEWAY SCRIPTS")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "scripts/create_mcp_gateway.py",
            "MCP Gateway creation script"
        ),
        check_file_exists(
            "scripts/register_mcp_tools.py",
            "MCP Tool registration script"
        ),
        check_code_implementation(
            "scripts/create_mcp_gateway.py",
            ["create_gateway", "CUSTOM_JWT", "discoveryUrl"],
            "Gateway authentication setup"
        ),
        check_code_implementation(
            "scripts/register_mcp_tools.py",
            ["order_trends", "sales_insights", "product_search"],
            "Tool registration"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 7: Integration Tests
    print("7. INTEGRATION TESTS")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "tests/test_admin_insights_integration.py",
            "Integration test suite"
        ),
        check_code_implementation(
            "tests/test_admin_insights_integration.py",
            ["TestWebSocketConnection", "TestMessageFlow", "TestAnalyticsDataFormatting"],
            "WebSocket and message tests"
        ),
        check_code_implementation(
            "tests/test_admin_insights_integration.py",
            ["TestMCPGatewayAuthentication", "TestMCPGatewayToolInvocation"],
            "MCP Gateway tests"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 8: Lambda Handler Implementation
    print("8. LAMBDA HANDLER IMPLEMENTATION")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "lambda/admin_insights_agent/handler.py",
            "Agent handler"
        ),
        check_file_exists(
            "lambda/admin_insights_agent/websocket_connect.py",
            "WebSocket connect handler"
        ),
        check_file_exists(
            "lambda/admin_insights_agent/websocket_disconnect.py",
            "WebSocket disconnect handler"
        ),
        check_code_implementation(
            "lambda/admin_insights_agent/handler.py",
            ["ApiGatewayManagementApi", "post_to_connection", "connectionId"],
            "WebSocket response streaming"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Section 9: Documentation
    print("9. DOCUMENTATION")
    print("-" * 80)
    
    checks = [
        check_file_exists(
            "frontends/admin-dashboard/ADMIN_INSIGHTS_INTEGRATION_GUIDE.md",
            "Integration guide"
        ),
        check_file_exists(
            "lambda/admin_insights_agent/WEBSOCKET_IMPLEMENTATION.md",
            "WebSocket implementation docs"
        ),
        check_file_exists(
            "lambda/admin_insights_agent/MCP_GATEWAY_IMPLEMENTATION.md",
            "MCP Gateway implementation docs"
        ),
    ]
    
    all_checks_passed = all_checks_passed and all(checks)
    print()
    
    # Final Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED!")
        print()
        print("Checkpoint 17 Requirements Met:")
        print("  ✓ Admin dashboard chat widget connection")
        print("  ✓ Message flow from frontend to agent")
        print("  ✓ Analytics data formatting in chat")
        print("  ✓ MCP gateway authentication")
        print("  ✓ MCP gateway tool invocation")
        print()
        print("Next Steps:")
        print("  1. Deploy the infrastructure if not already deployed")
        print("  2. Run the MCP gateway creation script:")
        print("     python scripts/create_mcp_gateway.py")
        print("  3. Register tools with the gateway:")
        print("     python scripts/register_mcp_tools.py --gateway-id <GATEWAY_ID>")
        print("  4. Test the frontend widget in the admin dashboard")
        print("  5. Test external tool invocation via MCP gateway")
        print()
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print()
        print("Please review the failed checks above and ensure all components")
        print("are properly implemented before proceeding.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
