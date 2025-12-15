// AWS Amplify v6 configuration for Cognito and API Gateway
export const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_APP_CLIENT_ID,
      region: import.meta.env.VITE_AWS_REGION,
      signUpVerificationMethod: 'code',
      loginWith: {
        email: true,
        username: false,
      },
    },
  },
  API: {
    REST: {
      ECom67Api: {
        endpoint: import.meta.env.VITE_API_GATEWAY_ENDPOINT,
        region: import.meta.env.VITE_AWS_REGION,
      },
    },
  },
};

export const apiConfig = {
  endpoint: import.meta.env.VITE_API_GATEWAY_ENDPOINT,
  region: import.meta.env.VITE_AWS_REGION,
};
