# Post-Authentication Trigger - Testing Guide

## Overview
The post-authentication Lambda trigger automatically saves user information to DynamoDB after successful signup or login.

## What Was Implemented

### 1. Lambda Function (`lambda/post_auth/index.py`)
- Triggered after user authentication
- Saves user profile to `e-com67-users` DynamoDB table
- Handles both new user creation and existing user login updates
- Non-blocking: doesn't fail authentication if DB write fails

### 2. CDK Stack Updates (`e_com67/stacks/data_stack.py`)
- Added Lambda layer (AWS Powertools)
- Created post-auth Lambda function
- Configured Cognito trigger
- Granted necessary IAM permissions

## Deployment Steps

### 1. Deploy the Updated Stack
```bash
cd backend
source .venv/bin/activate  # Activate virtual environment
cdk deploy ECom67-DataStack
```

### 2. Verify Deployment
```bash
# Check if Lambda function was created
aws lambda list-functions --query 'Functions[?contains(FunctionName, `PostAuth`)].FunctionName'

# Check Cognito trigger configuration
aws cognito-idp describe-user-pool \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --query 'UserPool.LambdaTriggers'
```

## Testing the Trigger

### Method 1: Local Testing (Pre-Deployment)
```bash
cd backend
python scripts/test_post_auth.py
```

**Note:** This requires:
- AWS credentials configured
- DynamoDB table `e-com67-users` exists
- Proper IAM permissions for local testing

### Method 2: End-to-End Testing via Frontend

#### Step 1: Start Frontend
```bash
cd frontend
npm start
```

#### Step 2: Sign Up a New User
1. Navigate to `http://localhost:3000`
2. Click "Sign Up"
3. Enter email and password (min 8 chars, uppercase, lowercase, digit)
4. Check email for verification code
5. Verify email
6. Log in with credentials

#### Step 3: Verify User in DynamoDB
```bash
# Get your user pool ID
aws cognito-idp list-user-pools --max-results 10

# List users
aws cognito-idp list-users --user-pool-id <YOUR_USER_POOL_ID>

# Check DynamoDB for the user (get sub/userId from above)
aws dynamodb get-item \
  --table-name e-com67-users \
  --key '{"userId": {"S": "<USER_SUB_ID>"}}'
```

Expected DynamoDB Item:
```json
{
  "userId": "12345678-1234-1234-1234-123456789012",
  "email": "user@example.com",
  "emailVerified": true,
  "name": "",
  "phone": "",
  "createdAt": 1734307200,
  "lastLogin": 1734307200,
  "role": "customer",
  "preferences": {
    "notifications": true,
    "newsletter": true
  }
}
```

### Method 3: Test via AWS Console

#### Step 1: Trigger via Cognito Console
1. Go to AWS Cognito Console
2. Select your user pool
3. Create a test user or use existing user
4. Sign in as that user

#### Step 2: Check CloudWatch Logs
```bash
# Get log group
aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `PostAuth`)].logGroupName'

# Tail logs
aws logs tail /aws/lambda/ECom67-DataStack-PostAuthFunction --follow
```

Expected log output:
```
Post-auth trigger event: {...}
Creating new user profile: 12345678-1234-1234-1234-123456789012
User profile created successfully for: user@example.com
```

### Method 4: Manual Lambda Invocation

Create a test event file `test-event.json`:
```json
{
  "version": "1",
  "triggerSource": "PostAuthentication_Authentication",
  "region": "us-east-1",
  "userPoolId": "us-east-1_xxxxx",
  "userName": "test-user",
  "request": {
    "userAttributes": {
      "sub": "test-uuid-12345",
      "email": "test@example.com",
      "email_verified": "true",
      "name": "Test User"
    }
  },
  "response": {}
}
```

Invoke the Lambda:
```bash
aws lambda invoke \
  --function-name <POST_AUTH_FUNCTION_NAME> \
  --payload file://test-event.json \
  response.json

cat response.json
```

## Verification Checklist

- [ ] Lambda function deployed successfully
- [ ] Cognito trigger configured (check Cognito console)
- [ ] IAM permissions granted (Lambda can write to DynamoDB)
- [ ] New user signup creates entry in DynamoDB
- [ ] Existing user login updates `lastLogin` timestamp
- [ ] Email field is correctly saved
- [ ] CloudWatch logs show successful execution
- [ ] No authentication failures due to trigger errors

## Troubleshooting

### Issue: Lambda not triggered
**Solution:** Check Cognito User Pool triggers in AWS Console

```bash
aws cognito-idp describe-user-pool --user-pool-id <ID> --query 'UserPool.LambdaTriggers'
```

### Issue: Permission denied writing to DynamoDB
**Solution:** Verify IAM role has DynamoDB write permissions

```bash
aws iam get-role-policy \
  --role-name <LAMBDA_ROLE_NAME> \
  --policy-name <POLICY_NAME>
```

### Issue: User not appearing in DynamoDB
**Solution:** Check CloudWatch logs for errors

```bash
aws logs tail /aws/lambda/ECom67-DataStack-PostAuthFunction --follow
```

### Issue: Authentication fails after adding trigger
**Solution:** Check Lambda returns event unchanged (critical requirement)

The Lambda must return the original event object for Cognito to proceed.

## Next Steps

After successful testing:
1. Update frontend to display user profile information
2. Add user profile edit functionality
3. Consider adding more user attributes (address, preferences, etc.)
4. Implement user profile API endpoints
5. Add analytics tracking for user signups

## Clean Up (Development Only)

To remove the trigger:
```bash
# Update data_stack.py and remove lambda_triggers parameter
# Then redeploy
cdk deploy ECom67-DataStack
```
