import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 3000,
      open: true,
    },
    define: {
      'process.env.VITE_API_GATEWAY_ENDPOINT': JSON.stringify(env.VITE_API_GATEWAY_ENDPOINT),
      'process.env.VITE_COGNITO_USER_POOL_ID': JSON.stringify(env.VITE_COGNITO_USER_POOL_ID),
      'process.env.VITE_COGNITO_APP_CLIENT_ID': JSON.stringify(env.VITE_COGNITO_APP_CLIENT_ID),
      'process.env.VITE_AWS_REGION': JSON.stringify(env.VITE_AWS_REGION),
    },
  };
});
