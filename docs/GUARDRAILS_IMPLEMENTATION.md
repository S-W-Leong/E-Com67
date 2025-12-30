# Guardrails Implementation Summary

## Overview

This document describes the implementation of AWS Bedrock Guardrails integration for the Admin Insights Agent. The implementation ensures that all user inputs and agent outputs are scanned for PII (Personally Identifiable Information) and prompt injection attacks.

## Requirements Addressed

- **Requirement 5.1**: PII detection in user input ✅
- **Requirement 5.2**: PII blocking/redaction ✅
- **Requirement 5.3**: Prompt injection detection ✅
- **Requirement 5.4**: Attack request rejection ✅
- **Requirement 5.5**: Output PII scanning ✅

## Implementation Details

### 1. Guardrails Function (`apply_guardrails`)

**Location**: `lambda/admin_insights_agent/agent.py`

**Purpose**: Apply Bedrock Guardrails to content for PII detection and prompt attack prevention.

**Key Features**:
- Scans both INPUT (user messages) and OUTPUT (agent responses)
- Detects PII entities (email, phone, credit cards, etc.)
- Detects prompt injection attacks
- Returns structured results with action and violations
- Handles guardrail service errors gracefully (blocks content on error)

**Return Format**:
```python
{
    "action": "NONE" | "BLOCKED",
    "content": str,  # Original or redacted content
    "violations": List[str]  # List of detected violations
}
```

### 2. Custom Exception (`GuardrailViolationError`)

**Location**: `lambda/admin_insights_agent/agent.py`

**Purpose**: Provide explicit exception type for guardrail violations.

**Attributes**:
- `message`: Human-readable error message
- `violations`: List of specific violations detected
- `source`: Whether violation was in INPUT or OUTPUT

**Benefits**:
- Clear distinction from other ValueError exceptions
- Structured violation information for logging and metrics
- Easier error handling in the handler

### 3. Message Processing Pipeline (`process_message`)

**Location**: `lambda/admin_insights_agent/agent.py`

**Pipeline Steps**:

1. **Input Guardrails**: Scan user message before processing
   - If BLOCKED: Raise `GuardrailViolationError`
   - If NONE: Continue to agent processing

2. **Agent Processing**: Invoke agent with validated input
   - Agent processes message and generates response
   - Tools may be invoked as needed

3. **Output Guardrails**: Scan agent response before returning
   - If BLOCKED: Replace response with safe message
   - If NONE: Return original response

4. **Return Result**: Formatted response with metadata

### 4. Handler Error Handling (`handle_agent_processing`)

**Location**: `lambda/admin_insights_agent/handler.py`

**Guardrail Error Handling**:
- Catches `GuardrailViolationError` exceptions
- Emits CloudWatch metric: `GuardrailBlocked`
- Determines specific error code:
  - `PII_DETECTED`: If PII violations found
  - `PROMPT_ATTACK_DETECTED`: If prompt attack detected
  - `CONTENT_BLOCKED`: Generic content block
- Returns 400 Bad Request with violation details
- Sends error message to WebSocket connection

**Error Response Format**:
```json
{
  "error": {
    "code": "PII_DETECTED",
    "message": "Your request contains content that cannot be processed...",
    "timestamp": 1234567890,
    "requestId": "uuid",
    "details": {
      "violations": ["PII detected: EMAIL"],
      "source": "INPUT"
    }
  }
}
```

## Guardrail Configuration

**CDK Stack**: `stacks/admin_insights_stack.py`

**Policies Configured**:

1. **PII Detection**:
   - Email addresses
   - Phone numbers
   - Credit card numbers
   - Action: BLOCK

2. **Prompt Attack Prevention**:
   - Jailbreak attempts
   - Prompt injection
   - Prompt leakage
   - Filter Strength: MEDIUM
   - Applied to: INPUT only

**Environment Variables**:
- `GUARDRAIL_ID`: Bedrock Guardrail identifier
- `GUARDRAIL_VERSION`: Guardrail version (default: "DRAFT")

## Testing

**Test File**: `tests/test_admin_insights_guardrails.py`

**Test Coverage**:

1. ✅ `test_apply_guardrails_no_violations`: Clean content passes
2. ✅ `test_apply_guardrails_pii_detected`: PII is detected and blocked
3. ✅ `test_apply_guardrails_prompt_attack_detected`: Prompt attacks detected
4. ✅ `test_apply_guardrails_output_scanning`: Output content is scanned
5. ✅ `test_apply_guardrails_no_guardrail_configured`: Graceful handling when not configured
6. ✅ `test_apply_guardrails_service_error`: Service errors handled safely
7. ✅ `test_process_message_input_blocked`: Input violations raise exception
8. ✅ `test_process_message_output_blocked`: Output violations replace response
9. ✅ `test_process_message_both_guardrails_pass`: Clean messages pass through

**All tests passing**: 9/9 ✅

## Security Considerations

1. **Fail-Safe Design**: If guardrail service fails, content is BLOCKED by default
2. **No PII Logging**: Violation details are logged without exposing actual PII
3. **Dual Scanning**: Both input and output are scanned independently
4. **Graceful Degradation**: System continues to work if guardrails not configured (with warning)
5. **Structured Errors**: Clear error messages without revealing system internals

## Monitoring and Observability

**CloudWatch Metrics**:
- `GuardrailBlocked`: Count of blocked requests
- `Error_PII_DETECTED`: Count of PII violations
- `Error_PROMPT_ATTACK_DETECTED`: Count of prompt attack attempts
- `Error_CONTENT_BLOCKED`: Count of generic content blocks

**Logging**:
- Input guardrail checks logged with session context
- Output guardrail checks logged with session context
- Violations logged with sanitized details (no PII exposed)
- Guardrail service errors logged for investigation

## Usage Example

```python
# In agent.py - process_message function

# Step 1: Apply input guardrails
input_result = apply_guardrails(message, source="INPUT")
if input_result["action"] == "BLOCKED":
    raise GuardrailViolationError(
        message="Your request contains content that cannot be processed.",
        violations=input_result["violations"],
        source="INPUT"
    )

# Step 2: Process with agent
response = agent.process(message)

# Step 3: Apply output guardrails
output_result = apply_guardrails(response, source="OUTPUT")
if output_result["action"] == "BLOCKED":
    response = "I apologize, but I cannot provide this information..."
else:
    response = output_result["content"]
```

## Future Enhancements

1. **Custom PII Patterns**: Add domain-specific PII patterns
2. **Redaction Instead of Blocking**: Option to redact PII instead of blocking
3. **Guardrail Metrics Dashboard**: Dedicated CloudWatch dashboard
4. **Violation Alerts**: SNS notifications for repeated violations
5. **User Feedback**: Allow users to report false positives

## Deployment Notes

1. Ensure `GUARDRAIL_ID` environment variable is set in Lambda configuration
2. Verify IAM role has `bedrock:ApplyGuardrail` permission
3. Test guardrails with sample PII and prompt attacks before production
4. Monitor `GuardrailBlocked` metric for false positives
5. Review guardrail configuration periodically for effectiveness

## References

- AWS Bedrock Guardrails Documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- Design Document: `.kiro/specs/admin-insights-agent/design.md`
- Requirements Document: `.kiro/specs/admin-insights-agent/requirements.md`
